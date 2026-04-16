import requests
from PIL import Image

from backend.shared.job_queue import get_job

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
    response = requests.get(url)
    response.raise_for_status() # Check if request was successful

    # Save image to a file and send to uploader
    with open(f'{fighter_id}.jpg', 'wb') as f:
        for chunk in response.iter_content(1024):
            pass
