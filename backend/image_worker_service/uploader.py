import os

import requests
import yaml
from services.supabase import supabase

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)
BASE_API_URL = config['base_api_url']

BUCKET_NAME = os.environ.get("SUPABASE_FIGHTER_IMAGE_BUCKET")
uploader_service_key = os.getenv("UPLOADER_SERVICE_KEY")

def upload_img(file_path, file, content_type, fighter_id):
    '''
        Uploads image file to Supabase storage bucket.
    '''
    # Upload image to Supabase storage bucket
    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path, 
            file=file,
            file_options={
                "content-type": content_type,
                "upsert": "true"
            }
            
            )
        
        update_fighter_img_url(fighter_id, file_path)
    except Exception as e:
        print(f"Error uploading image to {BUCKET_NAME}/{file_path}: {e}")

def update_fighter_img_url(fighter_id, img_url):
    '''
        Calls api to update fighter image url.
        Parameters: 
            fighter_id (int): ID of fighter to update image URL for
            img_url (str): URL of fighter image to update in database
    '''
    try:
        res = requests.patch(
            BASE_API_URL + f"{fighter_id}/SetFighterImage",
            headers={'Authorization': f'Api-Key {uploader_service_key}'},
            json={'img_url': img_url}
        )

        if not res.ok:
            print(f"Failed to update fighter image URL for fighter ID {fighter_id}. Response: {res.text}")
            
        res.raise_for_status()
        print(f"Image uploaded successfully to {BUCKET_NAME}/{img_url}") 
    except Exception as e:
        print(f"Error updating fighter image URL for fighter ID {fighter_id}: {e}")