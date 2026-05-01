package main

import (
	"fmt"
	"net/http"
	"os"
	"strings"
)

func UpdateFighterImageURL(fighterID int64, supabasePath string) error {
	/*
		Updates the fighter image URL in the API.
		PARAMS:
		- fighterID: ID of the fighter
		- supabasePath: Path of the image in the Supabase storage bucket
		RETURNS:
		- error: Error if any
	*/

	url := fmt.Sprintf("%s/api/fighters/%d/SetFighterImage", os.Getenv("BASE_API_URL"), fighterID) // Format the URL for the API call

	body := strings.NewReader(`{"img_url":"` + supabasePath + `"}`) // Create the JSON data for the API call

	req, err := http.NewRequest("PATCH", url, body) // Create the request for the API call
	if err != nil {
		return fmt.Errorf("error creating request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")                            // Set the content type for the request
	req.Header.Set("Authorization", "Api-Key "+os.Getenv("UPLOADER_SERVICE_KEY")) // Set the authorization header for the request

	client := &http.Client{}    // Create a new HTTP client
	resp, err := client.Do(req) // Do the request
	if err != nil {
		return fmt.Errorf("error doing request: %v", err)
	}
	defer resp.Body.Close() // Close the response body

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("error updating fighter image URL: %d", resp.StatusCode)
	}

	return nil
}
