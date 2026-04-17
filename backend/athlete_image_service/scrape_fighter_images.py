from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
import yaml
import os
import threading
from .parser import parse_html
from backend.shared.job_queue import publish_job
from backend.image_worker_service.downloader import consume_jobs

image_service_key = os.getenv("IMAGE_SERVICE_KEY")
uploader_service_key = os.getenv("UPLOADER_SERVICE_KEY")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

ALL_FIGHTERS_URL = config['all_fighters_url']
HEADERS = config['headers']
API_URL = config['api_url']

url_params = {
    "view_name": "all_athletes",
    "view_display_id": "page",
    "view_args": "",
    "view_path": "/athletes/all",
    "view_base_path": "",
    "page": 0,
    "pager_element": "0",
    "ajax_page_state[theme]": "ufc",
    "ajax_page_state[theme_token]": ""
}

def scrape_fighter_images_df():
    """
    Scrapes the UFC website for all fighters and returns a set of their normalized names and image URLs.
    """
    # Get fighters with missing images from API
    fighters = get_fighters_with_missing_images()

    # If no fighters with missing images found, no need to run pipeline
    if not fighters:
        print("No fighters with missing images found in database.")
        return
    else:
        print("Scraping fighter images...")

        # Convert JSON string to python object
        fighter_with_missing_images = {}
        for fighter in fighters:
            fighter_with_missing_images[fighter['normalized_name']] = {"fighter_id": fighter['fighter_id'], "img_url": None}

        # Initialize session and make initial request to get necessary parameters for AJAX requests
        session = requests.Session()
        response = session.get(ALL_FIGHTERS_URL, headers=HEADERS)
        response.raise_for_status()
        
        # Parse response to extract required parameters
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find drupal settings script tag and parse JSON
        drupal_settings_tag = soup.find("script", {"data-drupal-selector": "drupal-settings-json"})
        drupal_settings = json.loads(drupal_settings_tag.string)
        
        # Extract and add to url_params
        url_params["ajax_page_state[libraries]"] = drupal_settings["ajaxPageState"]["libraries"]
        
        ajax_views = drupal_settings["views"]["ajaxViews"]
        first_view = next(iter(ajax_views.values()))
        url_params["view_dom_id"] = first_view["view_dom_id"]

        response_list = []
        page = 0
        
        # Loop through pages until no more fighters are found
        while True:
            url_params["page"] = page
            response = session.get(ALL_FIGHTERS_URL, params=url_params, headers=HEADERS)
            soup = BeautifulSoup(response.text, "html.parser")
            
            fighter_card = soup.select(".c-listing-athlete-flipcard__front")
            if not fighter_card:
                break
            
            # Submit html soup to parser to extract fighter names and image urls
            parsed_response = parse_html(soup)

            # Iterate through parsed response and add fighter ids to each object if normalized name is in list of fighters
            for res in parsed_response:
                normalized_name = res['normalized_name']# gets normalized name from parsed response
                fighter_id = get_fighter_id(fighter_with_missing_images, normalized_name)# gets fighter id from lookup function

                # If id does not exist or image url is null, skip fighter
                if fighter_id is None or res['img_url'] is None:
                    continue
                res['fighter_id'] = fighter_id
                publish_job(res) # publish job to queue for worker to consume

            page += 1 # Increment page number for next request

def get_fighters_with_missing_images():
    '''
        Makes a request to the API to get all fighters in the db that are missing image url's
        RETURNS: A list ofjson objects of fighter rows with fighter_id and normalized_name fields
    '''
    try:
        response = requests.get(
            API_URL,
            headers={'Authorization': f'Api-Key {image_service_key}'})
    except requests.RequestException as e:
        print(f"Error fetching fighter image candidates: {e}")
    

    return response.json()

def get_fighter_id(lookup, normalized_name):
    '''
        Helper function that takes in a normalized name and returns the corresponding fighter id from the lookup dictionary
    '''
    # Checks if normalized name exists in lookup dictionary and returns fighter id if it does 
    key = lookup.get(normalized_name) 
    if key: 
        return lookup.get(normalized_name).get("fighter_id")
    return None

if __name__ == "__main__":
    thread = threading.Thread(target=consume_jobs, daemon=True)
    thread.start()

    scrape_fighter_images_df()