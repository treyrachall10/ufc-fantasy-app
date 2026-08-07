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
	workerCount := 10                                        // Number of workers to start
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")           // Project ID from environment variables
	subscriptionID := os.Getenv("PUBSUB_IMAGE_SUBSCRIPTION") // Subscription ID from environment variables
	topicID := os.Getenv("PUBSUB_IMAGE_JOB_TOPIC")           // Topic ID from environment variables

	fmt.Println("Image worker service starting...")

	// Create postgres client
	pool, err := supabase.NewPostgresClient() // Create postgres client
	if err != nil {
		log.Fatalf("Failed to create postgres client: %v", err)
	}
	defer pool.Close() // Close postgres client

	// Create pubsub client and subscription
	ctx, cancel := context.WithCancel(context.Background())
	client, err := pubsub.NewClient(ctx, projectID) // Create Pubsub client
	if err != nil {
		log.Fatalf("Failed to create pubsub client: %v", err)
	}
	publisher := client.Publisher(topicID) // Create publisher for topic

	connection := types.Connection{
		Client:    client,
		Publisher: publisher,
		Pool:      pool,
	}

	defer client.Close() // Close Pubsub client at end of function

	// Create channel for successful jobs.
	channels := types.Channels{
		Success: make(chan Job),
	}

	var SuccessWorkerwg sync.WaitGroup  // Create wait group to wait for all success workers to finish
	var jobsEnqueued int64              // Create counter to track number of jobs enqueued

	// Start the success worker
	SuccessWorkerwg.Add(1)
	go successWorker(channels.Success, &SuccessWorkerwg, pool) // Start success worker

	// Consume queue messages and feed the worker channel.
	ConsumeJobs(connection, ctx, cancel, channels, &jobsEnqueued, subscriptionID, workerCount)

	close(channels.Success) // Close the success channel to signal the success worker to finish
	SuccessWorkerwg.Wait()
}

// ConsumeJobs handles pubsub communication and sends jobs to dataChannel.
func ConsumeJobs(
	connection types.Connection,
	ctx context.Context,
	cancel context.CancelFunc,
	channels types.Channels,
	jobsEnqueued *int64,
	subscriptionID string,
	workerCount int) {
	/*
		Consumes messages from the pubsub subscription and sends them to the dataChannel.
		Shuts down the consumer if no messages are received in the last 60 seconds.

		PARAMS:
		- connection: Connection to the pubsub and postgres database
		- ctx: Context
		- cancel: Cancel function
		- channels: Channels to receive and send jobs from
		- jobsEnqueued: Counter to track number of jobs enqueued
		- subscriptionID: Subscription ID
	*/

	timeSinceLastMessage := time.Now()
	idleShutdownEnabled := envBool("WORKER_IDLE_SHUTDOWN_ENABLED", true)
	idleTimeout := envDurationSeconds("WORKER_IDLE_TIMEOUT_SECONDS", 60*time.Second)
	idleCheckInterval := envDurationSeconds("WORKER_IDLE_CHECK_INTERVAL_SECONDS", 10*time.Second)

	// Optionally shut down after an idle period with no messages.
	go func() {
		if !idleShutdownEnabled {
			return
		}
		for {
			if time.Since(timeSinceLastMessage) > idleTimeout {
				fmt.Printf(
					"No messages received in the last %s. Shutting down consumer.\n",
					idleTimeout,
				)
				cancel()
				return
			}
			time.Sleep(idleCheckInterval)
		}
	}()

	sub := connection.Client.Subscriber(subscriptionID) // Get subscription from client
	sub.ReceiveSettings.MaxExtension = 2 * time.Minute  // Set the maximum extension to 2 minutes
	sub.ReceiveSettings.MaxOutstandingMessages = workerCount // Set outstanding messages to worker capacity

	err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		timeSinceLastMessage = time.Now() // Update time since last message was received
		var job Job                       // Create a new job
		err := json.Unmarshal(msg.Data, &job) // Unmarshal the message data into the job
		if err != nil {
			log.Printf("Failed to unmarshal message: %v", err)
			msg.Nack() // Nack the message to put it back in the subscription
			return
		}

		job.Msg = msg

		err = downloadImageWorker(job, channels.Success)
		if err != nil {
			job.ErrorMsg = err.Error()
			if failErr := handleFailedJob(&job, job.ErrorMsg, connection.Pool, connection.Publisher); failErr != nil {
				log.Printf("Failed to handle failed job %d: %v", job.ID, failErr)
				msg.Nack()
				return
			}
		}

		msg.Ack() // Ack only after processing (or failed-job handling) is complete
		atomic.AddInt64(jobsEnqueued, 1)
	})
	if err != nil {
		log.Fatalf("Failed to receive message: %v", err)
	}
}

// downloadImageWorker processes one image job and returns an error on failure.
func downloadImageWorker(
	job Job,
	successChannel chan Job) error {
	/*
		Processes a single image job.

		PARAMS:
		- job: Image job to process
		- successChannel: Channel to send successful jobs to
	*/

	supabaseClient := supabase.NewStorageClient() // Create Supabase client

	err := downloadImage(job, supabaseClient, successChannel) // Download the image
	if err != nil {
		fmt.Printf("Image job failed | id=%d fighter=%s error=%v\n",
			job.ID,
			job.NormalizedName,
			err,
		)
		return err
	}

	return nil
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

func envBool(name string, defaultValue bool) bool {
	raw := strings.TrimSpace(os.Getenv(name))
	if raw == "" {
		return defaultValue
	}
	switch strings.ToLower(raw) {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		log.Printf("Invalid %s=%q; using default %v", name, raw, defaultValue)
		return defaultValue
	}
}

func envDurationSeconds(name string, defaultValue time.Duration) time.Duration {
	raw := strings.TrimSpace(os.Getenv(name))
	if raw == "" {
		return defaultValue
	}
	seconds, err := time.ParseDuration(raw + "s")
	if err != nil || seconds <= 0 {
		log.Printf("Invalid %s=%q; using default %s", name, raw, defaultValue)
		return defaultValue
	}
	return seconds
}
