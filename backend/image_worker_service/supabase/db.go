package supabase

import (
	"context"
	"fmt"
	"log"
	"os"

	"image-worker/types"

	"github.com/jackc/pgx/v5"
)

func NewPostgresClient() *pgx.Conn {
	conn, err := pgx.Connect(context.Background(), os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	log.Println("Connected to database")
	return conn
}

func BulkUpdateImageJobs(conn *pgx.Conn, jobs []types.ImageJob) error {

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

	_, err := conn.Exec(context.Background(), query, args...)
	if err != nil {
		return err
	}
	return nil
}

func generateBulkSQLSring(length int) string {
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
	// Generate the arguments list for the query
	args := make([]interface{}, 0)
	for _, job := range jobs {
		args = append(args, job.ID, job.FighterID, job.SupabasePath)
	}
	return args
}
