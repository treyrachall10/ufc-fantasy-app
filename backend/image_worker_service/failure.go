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

func handleFailedJob(job *types.ImageJob, errMsg string, pool *pgxpool.Pool, publisher *pubsub.Publisher) error {
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
		return fmt.Errorf("handleFailedJob received nil job")
	}

	fmt.Printf("Job failed for %s: %s\n", job.NormalizedName, errMsg)

	// If the retry count is less than 3, increment the retry count, update the job in the database and nack the message
	if job.RetryCount < 3 {
		retryCount, err := supabase.UpdateFailedImageJob(pool,
			job,
			`UPDATE worker.image_job
			SET status = 'FAILED',
			retry_count = retry_count + 1,
			updated_at = NOW(),
			error_msg = $1::text
			WHERE id = $2::bigint
			RETURNING retry_count`)
		if err != nil {
			return fmt.Errorf("error updating failed job %d: %w", job.ID, err)
		}
		job.RetryCount = retryCount
		data, err := json.Marshal(job)
		if err != nil {
			return fmt.Errorf("error marshaling failed job %d: %w", job.ID, err)
		}
		if _, err := publisher.Publish(context.Background(), &pubsub.Message{
			Data: data,
		}).Get(context.Background()); err != nil {
			return fmt.Errorf("error republishing failed job %d: %w", job.ID, err)
		}
	}

	// If the retry count is greater than or equal to 3, update the job in the database and ack the message
	if job.RetryCount >= 3 {
		_, err := supabase.UpdateFailedImageJob(pool,
			job,
			`UPDATE worker.image_job
			SET status = 'DEAD',
			updated_at = NOW(),
			error_msg = $1::text
			WHERE id = $2::bigint
			RETURNING retry_count`)
		if err != nil {
			return fmt.Errorf("error updating dead job %d: %w", job.ID, err)
		}
	}

	return nil
}
