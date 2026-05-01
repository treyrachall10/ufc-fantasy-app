package supabase

import (
	"context"
	"fmt"
	"log"
	"os"

	"image-worker/types"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

func NewPostgresClient() *pgxpool.Pool {
	/*
		Creates a new postgres client.
		PARAMS:
			- None
		RETURNS:
			- pool: Postgres connection
	*/

	config, err := pgxpool.ParseConfig(os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("Failed to parse database URL: %v", err)
	}

	config.ConnConfig.DefaultQueryExecMode = pgx.QueryExecModeSimpleProtocol
	pool, err := pgxpool.NewWithConfig(context.Background(), config)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	log.Println("Connected to database")
	return pool
}

func BulkUpdateImageJobs(pool *pgxpool.Pool, jobs []types.ImageJob) error {
	/*
		Bulk updates the image jobs in the database.
		PARAMS:
			- pool: Postgres connection
			- jobs: Jobs to update
		RETURNS:
			- err: Error if any
	*/

	args := generateArgsList(jobs)                // Generate the arguments list for the query
	sqlStrings := generateBulkSQLSring(len(jobs)) // Generate the SQL strings for the query

	// Build the query
	query := fmt.Sprintf(`
		UPDATE image_job as ij
		SET 
			status = 'COMPLETED',
			supabase_path = 'fighter-images/' || data.fighter_id || '/' || data.supabase_path,
			updated_at = NOW(),
			completed_at = NOW()
		FROM (
			VALUES %s
		) as data(id, fighter_id, supabase_path)
		WHERE ij.id = data.id::bigint
	`, sqlStrings)

	_, err := pool.Exec(context.Background(), query, args...)
	if err != nil {
		return err
	}
	return nil
}

func generateBulkSQLSring(length int) string {
	/*
		Generates the SQL strings for the query.
		PARAMS:
			- length: Length of the jobs
		RETURNS:
			- s: SQL strings
	*/

	paramIndex := 1
	s := ""
	// Loop through the length and generate the SQL strings
	for i := 0; i < length; i++ {
		s += fmt.Sprintf("($%d::bigint, $%d::bigint, $%d::text)", paramIndex, paramIndex+1, paramIndex+2) // Format the values for the query
		paramIndex += 3
		// Add comma between values
		if i < length-1 {
			s += ", "
		}
	}
	return s
}

func generateArgsList(jobs []types.ImageJob) []interface{} {
	/*
		Generates the arguments list for the query.
		PARAMS:
			- jobs: Jobs to generate the arguments list for
		RETURNS:
			- args: Arguments list
	*/

	// Generate the arguments list for the query
	args := make([]interface{}, 0)
	for _, job := range jobs {
		args = append(args, job.ID, job.FighterID, job.SupabasePath)
	}
	return args
}

func UpdateFailedImageJob(pool *pgxpool.Pool, job *types.ImageJob, query string) (int64, error) {
	/*
		Updates a failed image job in the database.
		PARAMS:
			- pool: Postgres connection
			- job: Image job
			- query: Query to update the image job
	*/
	var retryCount int64
	err := pool.QueryRow(context.Background(), query, job.ErrorMsg, job.ID).Scan(&retryCount) // Scan the retry count from the database
	if err != nil {
		return 0, err
	}
	fmt.Printf("Retry count for job %d: %d\n", job.ID, retryCount)
	return retryCount, nil
}
