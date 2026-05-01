package main

import (
	"context"
	"encoding/json"
	"fmt"
	"image-worker/supabase"
	"image-worker/types"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"cloud.google.com/go/pubsub/v2"
	storage_go "github.com/supabase-community/storage-go"
)

// Job is the payload consumed from the queue.
type Job = types.ImageJob

// main starts the worker service immediately on boot.
func main() {
	workerCount := 3                                         // Number of workers to start
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")           // Project ID from environment variables
	subscriptionID := os.Getenv("PUBSUB_IMAGE_SUBSCRIPTION") // Subscription ID from environment variables

	fmt.Println("Image worker service starting...")

	supabaseClient := supabase.NewStorageClient() // Create Supabase client

	// Create postgres client
	pool := supabase.NewPostgresClient() // Create postgres client
	defer pool.Close()                   // Close postgres client

	// Create pubsub client and subscription
	ctx, cancel := context.WithCancel(context.Background())
	client, err := pubsub.NewClient(ctx, projectID) // Create Pubsub client
	if err != nil {
		log.Fatalf("Failed to create pubsub client: %v", err)
	}

	defer client.Close() // Close Pubsub client at end of function

	dataChannel := make(chan Job)    // Create channel to send jobs to workers
	successChannel := make(chan Job) // Create channel to send successful jobs to

	var DownloadUploadwg sync.WaitGroup // Create wait group to wait for all downloder/uploaderworkers to finish
	var SuccessWorkerwg sync.WaitGroup  // Create wait group to wait for all success workers to finish
	var jobsEnqueued int64              // Create counter to track number of jobs enqueued

	// Start three workers immediately.
	for i := 0; i < workerCount; i++ {
		// Add worker to wait group
		DownloadUploadwg.Add(1)
		// Start worker
		go downloadImageWorker(i+1, dataChannel, successChannel, &DownloadUploadwg, supabaseClient, pool, publisher) // Start worker
	}

	// Start the success worker
	SuccessWorkerwg.Add(1)
	go successWorker(successChannel, &SuccessWorkerwg, pool) // Start success worker

	// Consume queue messages and feed the worker channel.
	ConsumeJobs(client, ctx, cancel, dataChannel, successChannel, &jobsEnqueued, subscriptionID, pool, publisher)

	// Wait for workers to finish after the channel is closed.
	DownloadUploadwg.Wait()
	close(successChannel) // Close the success channel to signal the success worker to finish
	SuccessWorkerwg.Wait()
	fmt.Printf("Total jobs put into worker channel: %d\n", atomic.LoadInt64(&jobsEnqueued))
}

// ConsumeJobs handles pubsub communication and sends jobs to dataChannel.
func ConsumeJobs(
	client *pubsub.Client,
	ctx context.Context,
	cancel context.CancelFunc,
	dataChannel chan Job,
	successChannel chan Job,
	jobsEnqueued *int64,
	subscriptionID string,
	pool *pgxpool.Pool,
	publisher *pubsub.Publisher) {
	/*
		Consumes messages from the pubsub subscription and sends them to the dataChannel.
		Shuts down the consumer if no messages are received in the last 30 seconds.

		PARAMS:
		- client: Pubsub client
		- ctx: Context
		- cancel: Cancel function
		- dataChannel: Channel to send jobs to workers
		- jobsEnqueued: Counter to track number of jobs enqueued
		- subscriptionID: Subscription ID
	*/

	timeSinceLastMessage := time.Now()                // Track time since last message was received
	timeSinceLastMessageThreshold := 30 * time.Second // Threshold for how long to wait before shutting down consumer

	// Start a goroutine to check for inactivity and shut down the consumer if no messages are received in the last 30 seconds
	go func() {
		for {
			if time.Since(timeSinceLastMessage) > timeSinceLastMessageThreshold {
				fmt.Println("No messages received in the last 30 seconds. Shutting down consumer.")
				close(dataChannel)
				cancel()
				return
			}
			time.Sleep(5 * time.Second)
		}
	}()

	sub := client.Subscriber(subscriptionID) // Get subscription from client
	// Receive messages from the subscription and send them to the dataChannel
	err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		timeSinceLastMessage = time.Now()     // Update time since last message was received
		defer msg.Ack()                       // Ack the message to remove it from the subscription
		var job Job                           // Create a new job
		err := json.Unmarshal(msg.Data, &job) // Unmarshal the message data into the job
		if err != nil {
			log.Printf("Failed to unmarshal message: %v", err)
			msg.Nack() // Nack the message to put it back in the subscription
			return
		}

		job.Msg = msg

		log.Println("Received message for:", job.NormalizedName)
		dataChannel <- job // Send the job to the dataChannel
		atomic.AddInt64(jobsEnqueued, 1)
	})
	if err != nil {
		log.Fatalf("Failed to receive message: %v", err)
	}
}

// downloadImageWorker consumes jobs and downloads each fighter image.
func downloadImageWorker(workerID int,
	dataChannel <-chan Job,
	successChannel chan Job,
	wg *sync.WaitGroup,
	supabaseClient *storage_go.Client,
	pool *pgxpool.Pool,
	publisher *pubsub.Publisher) {
	/*
		Consumes jobs from the dataChannel and downloads each fighter image.
		Shuts down the worker if a stop job is received.

		PARAMS:
		- workerID: ID of the worker
		- dataChannel: Channel to receive jobs from
		- successChannel: Channel to send successful jobs to
		- wg: Wait group to wait for all workers to finish
		- supabaseClient: Supabase client
		- pool: Postgres connection
		- publisher: Publisher for topic
	*/

	defer wg.Done() // Done the worker when the wait group is done

	// Loop through the dataChannel and download each image
	for job := range dataChannel {
		err := downloadImage(job, supabaseClient, successChannel) // Download the image
		if err != nil {
			fmt.Printf("Error downloading image for %s: %v\n", job.NormalizedName, err)
			job.Msg.Nack() // Nack the message to put it back in the subscription
			continue
		}

		job.Msg.Ack()
	}
	fmt.Println("Download worker exited")
}

// downloadImage fetches image bytes from URL and forwards to uploader.
func downloadImage(job Job, supabaseClient *storage_go.Client, successChannel chan Job) error {
	/*
		Downloads an image from the URL and forwards it to the uploader.
		PARAMS:
		- job: Job to download
		- supabaseClient: Supabase client
		- successChannel: Channel to send successful jobs to
	*/

	fighterName := strings.ReplaceAll(job.NormalizedName, " ", "_")  // Replace all spaces in the normalized name with underscores
	filePath := fmt.Sprintf("%d/%s.jpg", job.FighterID, fighterName) // Format the file path for the image

	if job.ImgURL == "" {
		return fmt.Errorf("missing image URL")
	}
	// Use net/http to download the image.
	resp, err := http.Get(job.ImgURL)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Check if the image was downloaded successfully
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("bad response status: %d", resp.StatusCode)
	}

	// Read the image body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading response body failed: %w", err)
	}

	// Get the content type of the image
	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "image/jpeg"
	}

	upsert := true // Set the upsert flag to true (Upsert = true) means that if the image already exists, it will be replaced

	// Create the file options for the image
	fileOptions := storage_go.FileOptions{
		ContentType: &contentType,
		Upsert:      &upsert,
	}

	// Send image to uploader
	err = UploadImage(filePath, body, fileOptions, job.FighterID, supabaseClient)
	if err != nil {
		return fmt.Errorf("error uploading image for %s: %v", fighterName, err)
	}
	log.Println("Image uploaded for:", job.NormalizedName)

	err = UpdateFighterImageURL(job.FighterID, filePath) // Update the fighter image URL in the API
	if err != nil {
		return fmt.Errorf("error updating fighter image URL: %v", err)
	}

	successChannel <- job // Send the job to the successChannel

	return nil
}
