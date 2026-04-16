from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
import yaml
from backend.shared.utils import normalize_name
import os

key = os.getenv("KEY")

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
                
            response_list.append(soup)
            page += 1

        fighter_images = [] # List to store dictionaries of fighter names and their corresponding image URLs

        # Extract all fighter names and image URLs from all pages
        for response in response_list:
            cards = response.find_all('div', class_='c-listing-athlete-flipcard__front') # Get all divs with fighter info

            if cards:

                # Loop through each div and extract fighter name and image URL
                for card in cards:
                    name = card.find('span', class_='c-listing-athlete__name').text.strip() # Get fighter name
                    img_url = card.find('img')['src'] if card.find('img') else None # Get image URL if it exists

                    # Only add to list if image URL exists
                    if img_url:
                        fighter_images.append({'Fighter Name': name, 'Image URL': img_url})
                        normalized_name = normalize_name(name)

                        # if normalized name is in list of fighters with missing images, add image url to that fighter's entry
                        if normalized_name in fighter_with_missing_images:
                            print(f"Adding image url for {normalized_name}")
                            fighter_with_missing_images[normalized_name]["img_url"] = img_url # Update img_url for fighter in dictionary
                    else:
                        continue
                    
        df = pd.DataFrame.from_dict(fighter_with_missing_images, orient='index') # Convert dictionary to dataframe
        print(df)

def get_fighters_with_missing_images():
    '''
        Makes a request to the API to get all fighters in the db that are missing image url's
        RETURNS: A list ofjson objects of fighter rows with fighter_id and normalized_name fields
    '''
    try:
        response = requests.get(
            API_URL,
            headers={'Authorization': f'Api-Key {key}'})
    except requests.RequestException as e:
        print(f"Error fetching fighter image candidates: {e}")
    

    return response.json()



scrape_fighter_images_df()