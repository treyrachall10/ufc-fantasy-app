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
