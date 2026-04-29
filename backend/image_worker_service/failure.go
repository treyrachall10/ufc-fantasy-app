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

	if job.RetryCount < 3 {
		job.RetryCount++
		if job.Msg != nil {
			job.Msg.Nack()
			return
		}
		fmt.Printf("Cannot nack job %d: message is nil\n", job.ID)
	}
}
