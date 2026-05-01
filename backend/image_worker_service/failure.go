package main

import (
	"context"
	"fmt"
	"image-worker/supabase"
	"image-worker/types"

	"encoding/json"

	"cloud.google.com/go/pubsub/v2"
	"github.com/jackc/pgx/v5/pgxpool"
)

func handleFailedJob(job *types.ImageJob, errMsg string, pool *pgxpool.Pool, publisher *pubsub.Publisher) {
	/*
			Handles a failed job by updating the job in the database and nack/acking the message.

		PARAMS:
		- job: Job to handle
		- errMsg: Error message
		- pool: Postgres connection
		- publisher: Publisher for topic
	*/

	if job == nil {
		fmt.Println("handleFailedJob received nil job")
		return
	}

	fmt.Printf("Job failed for %s: %s\n", job.NormalizedName, errMsg)

	// If the retry count is less than 3, increment the retry count, update the job in the database and nack the message
	if job.RetryCount < 3 {
		if job.Msg != nil {
			retryCount, err := supabase.UpdateFailedImageJob(pool,
				job,
				`UPDATE image_job
				SET status = 'FAILED',
				retry_count = retry_count + 1,
				updated_at = NOW(),
				error_msg = $1::text
				WHERE id = $2::bigint
				RETURNING retry_count`)
			if err != nil {
				fmt.Printf("Error updating failed job %d: %v\n", job.ID, err)
			}
			job.RetryCount = retryCount
			job.Msg.Ack() // Nack the message to put it back in the subscription
			data, _ := json.Marshal(job)
			publisher.Publish(context.Background(), &pubsub.Message{
				Data: data,
			})
			return
		}
	}

	// If the retry count is greater than or equal to 3, update the job in the database and ack the message
	if job.RetryCount >= 3 {
		if job.Msg != nil {
			_, err := supabase.UpdateFailedImageJob(pool,
				job,
				`UPDATE image_job
				SET status = 'DEAD',
				updated_at = NOW(),
				error_msg = $1::text
				WHERE id = $2::bigint
				RETURNING retry_count`)
			if err != nil {
				fmt.Printf("Error updating failed job %d: %v\n", job.ID, err)
			}
			job.Msg.Ack() // Ack the message to remove it from the subscription
			return
		}
	}
}
