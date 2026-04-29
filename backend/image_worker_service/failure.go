package main

import (
	"fmt"
	"image-worker/types"
)

func handleFailedJob(job *types.ImageJob, errMsg string) {
	if job == nil {
		fmt.Println("handleFailedJob received nil job")
		return
	}

	fmt.Printf("Job failed for %s: %s\n", job.NormalizedName, errMsg)

	// If the retry count is less than 3, increment the retry count, update the job in the database and nack the message
	if job.RetryCount < 3 {
		job.RetryCount++
		if job.Msg != nil {
			job.Msg.Nack() // Nack the message to put it back in the subscription
			return
		}
		fmt.Printf("Cannot nack job %d: message is nil\n", job.ID)
	}

	// If the retry count is greater than or equal to 3, update the job in the database and ack the message
	if job.RetryCount >= 3 {
		if job.Msg != nil {
			job.Msg.Ack() // Ack the message to remove it from the subscription
			return
		}
		fmt.Printf("Cannot ack job %d: message is nil\n", job.ID)
	}
}
