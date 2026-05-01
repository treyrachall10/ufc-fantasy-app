package main

import (
	"bytes"
	"fmt"

	storage_go "github.com/supabase-community/storage-go"
)

func UploadImage(filePath string, file []byte, fileOptions storage_go.FileOptions, fighterID int64, supabaseClient *storage_go.Client) error {
	/*
		Uploads an image to the Supabase storage bucket.

		PARAMS:
		- filePath: Path to the image file
		- file: Image file bytes
		- fileOptions: File options for the image
		- fighterID: ID of the fighter
		- supabaseClient: Supabase client
	*/

	const bucketName = "fighter-images" // Name of the bucket to upload the image to
	reader := bytes.NewReader(file)
	_, err := supabaseClient.UploadFile(bucketName, filePath, reader, fileOptions) // Upload the image to the bucket
	if err != nil {
		return fmt.Errorf("error uploading image for %d: %v", fighterID, err)
	}
	return nil
}
