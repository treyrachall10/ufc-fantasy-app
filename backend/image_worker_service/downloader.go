package main

import (
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"context"
	"cloud.google.com/go/pubsub/v1"
	"os"
)

const workerCount = 3
const projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
const subscriptionID = os.Getenv("PUBSUB_IMAGE_SUBSCRIPTION")

// Job is the payload consumed from the queue.
type Job struct {
	Type           string
	ImgURL         string
	FighterID      string
	NormalizedName string
}

// main starts the worker service immediately on boot.
func main() {
	fmt.Println("Image worker service starting...")

	// Create pubsub client and subscription
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		log.Fatalf("Failed to create pubsub client: %v", err)
	}
	defer client.Close()

	dataChannel := make(chan Job)

	var wg sync.WaitGroup
	var jobsEnqueued int64

	// Start three workers immediately.
	for i := 0; i < workerCount; i++ {
		wg.Add(1)
		go downloadImageWorker(i+1, dataChannel, &wg)
	}

	// Consume queue messages and feed the worker channel.
	ConsumeJobs(client, dataChannel, &jobsEnqueued)

	// Wait for workers to finish after the channel is closed.
	wg.Wait()
	fmt.Printf("Total jobs put into worker channel: %d\n", atomic.LoadInt64(&jobsEnqueued))
}

// ConsumeJobs handles pubsub communication and sends jobs to dataChannel.
func ConsumeJobs(client *pubsub.Client, ctx context.Context, dataChannel chan Job, jobsEnqueued *int64) {

	sub := client.Subscription(subscriptionID)// Get subscription from client

	for {
		fmt.Println("Waiting for job...")
		job := getJob(sub)

		// Keep parity with the Python behavior: nil means queue is done.
		if job == nil {
			fmt.Println("No more jobs to process. Exiting worker.")
			close(dataChannel)
			return
		}

		// If consumer sees stop, acknowledge and stop the program.
		if job.Type == "stop" {
			fmt.Println("Stop job received by consumer. Shutting down.")
			acknowledgeJob()
			close(dataChannel)
			return
		}

		// Send normal jobs to workers.
		dataChannel <- *job
		atomic.AddInt64(jobsEnqueued, 1)
	}
}

// downloadImageWorker consumes jobs and downloads each fighter image.
func downloadImageWorker(workerID int, dataChannel <-chan Job, wg *sync.WaitGroup) {
	defer wg.Done()

	for job := range dataChannel {
		// Always acknowledge queue completion for each dequeued job.
		func() {
			defer acknowledgeJob()

			// Worker-level stop handling.
			if job.Type == "stop" {
				fmt.Printf("Worker %d received stop job.\n", workerID)
				return
			}

			downloadImage(job)
		}()
	}
}

// downloadImage fetches image bytes from URL and forwards to uploader.
func downloadImage(job Job) {
	fighterName := strings.ReplaceAll(job.NormalizedName, " ", "_")
	filePath := fmt.Sprintf("%s/%s.jpg", job.FighterID, fighterName)

	// Use net/http to download the image.
	resp, err := http.Get(job.ImgURL)
	if err != nil {
		fmt.Printf("Error downloading image for %s from %s: %v\n", fighterName, job.ImgURL, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		fmt.Printf("Error downloading image for %s from %s: status %d\n", fighterName, job.ImgURL, resp.StatusCode)
		return
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Error reading image for %s from %s: %v\n", fighterName, job.ImgURL, err)
		return
	}

	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "image/jpeg"
	}

	// Send image to uploader (Go implementation can be replaced later).
	uploadImg(filePath, body, contentType, job.FighterID)
}

// getJob should read the next message from pubsub and map it to Job.
func getJob(sub *pubsub.Subscription, ctx context.Context) *Job {
	// TODO: implement pubsub queue read in Go.
	msg, err := sub.Receive(ctx)
	if err != nil {
		log.Fatalf("Failed to receive message: %v", err)
	}
	job := Job{
		Type: msg.Data,
		ImgURL: msg.Attributes["img_url"],
		FighterID: msg.Attributes["fighter_id"],
		NormalizedName: msg.Attributes["normalized_name"],
	}
	return &job
}

// acknowledgeJob should mark one queue message as completed.
func acknowledgeJob() {
	// TODO: implement queue ack in Go.
}

// uploadImg sends the downloaded image to storage.
func uploadImg(filePath string, file []byte, contentType string, fighterID string) {
	// TODO: implement uploader in Go (still mirrors Python upload_img call shape).
}
