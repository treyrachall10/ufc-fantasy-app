package main

import (
	"fmt"
	"image-worker/supabase"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
)

func successWorker(successChannel <-chan Job, wg *sync.WaitGroup, conn *pgx.Conn) {
	defer wg.Done()

	jobs := make([]Job, 0, 50)              // Create a slice to store the jobs
	timer := time.NewTimer(2 * time.Minute) // Create a timer to flush the jobs every 2 minutes
	defer timer.Stop()

	flushJobs := func() {
		// If there are no jobs, return
		if len(jobs) == 0 {
			return
		}

		err := supabase.BulkUpdateImageJobs(conn, jobs) // Bulk update the image jobs
		if err != nil {
			fmt.Printf("Failed to bulk update image jobs: %v\n", err)
			return
		}

		jobs = jobs[:0] // Clear the jobs slice
	}

	for {
		select {
		case job, ok := <-successChannel: // Receive a job from the successChannel
			// if channel closed and no jobs, flush the jobs and return
			if !ok {
				flushJobs()
				return
			}

			jobs = append(jobs, job) // Add the job to the jobs slice
			if len(jobs) >= 50 {     // If the jobs slice is greater than or equal to 50, flush the jobs
				flushJobs()
			}

			if !timer.Stop() { // Stop the timer if it is not stopped
				select {
				case <-timer.C: // If the timer is stopped, select the timer channel
					// Do nothing
				default:
				}
			}
			timer.Reset(2 * time.Minute)

		// If the timer is stopped, select the timer channel
		case <-timer.C:
			flushJobs()                  // Flush the jobs
			timer.Reset(2 * time.Minute) // Reset the timer to 2 minutes
		}
	}
}
