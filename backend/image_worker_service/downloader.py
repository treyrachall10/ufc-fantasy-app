from backend.shared.job_queue import get_job

def consume_jobs():
    '''
        Continuously consumes jobs from the worker queue and processes them. 
    '''
    while True:
        job = get_job()
        # Process the job
        download_image(job)

def download_image(job):
    '''
        Downloads image from given url in job, sends image file to uploader
    '''
