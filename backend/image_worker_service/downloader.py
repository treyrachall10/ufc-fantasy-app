import requests
from PIL import Image

from shared.job_queue import get_job, worker_queue
from .uploader import upload_img

def consume_jobs():
    '''
        Continuously consumes jobs from the worker queue and processes them. 
    '''
    while True:
        print("Waiting for job...")
        job = get_job()
        # Process the job
        download_image(job)

def download_image(job):
    '''
        Downloads image from given url in job, sends image file to uploader
    '''
    url = job['img_url']
    fighter_id = job['fighter_id']
    fighter_name = job['normalized_name']
    fighter_name = fighter_name.replace(" ", "_") # Replace spaces with underscores for file naming
    file_path = f"{fighter_id}/{fighter_name}.jpg" # Build file path for Supabase storage bucket

    try:

        response = requests.get(url)
        response.raise_for_status() # Check if request was successful

    except Exception as e:
        print(f"Error downloading image for {fighter_name} from {url}: {e}")

    # Send image to uploader
    upload_img(file_path=file_path, file=response.content, content_type=response.headers.get("Content-Type", "image/jpeg"))