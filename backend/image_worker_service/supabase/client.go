package supabase

import (
	"log"
	"os"

	storage_go "github.com/supabase-community/storage-go"
)

func NewStorageClient() *storage_go.Client {
	/*
		Creates a new Supabase storage client.
		PARAMS:
		- url: URL of the Supabase storage bucket
		- key: Key of the Supabase storage bucket
	*/

	url := os.Getenv("SUPABASE_URL")              // Get the URL of the Supabase storage bucket from the environment variables
	key := os.Getenv("SUPABASE_SERVICE_ROLE_KEY") // Get the key of the Supabase storage bucket from the environment variables

	if url == "" || key == "" {
		log.Fatal("Missing Supabase env vars") // Log an error if the URL or key is missing
	}

	// NOTE: must include /storage/v1
	storageURL := url + "/storage/v1" // Create the storage URL

	client := storage_go.NewClient(storageURL, key, nil) // Create the Supabase storage client

	return client
}
