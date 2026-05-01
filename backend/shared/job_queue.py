import queue

worker_queue = queue.Queue()

def publish_job(job):
    '''
        Publishes a job to the worker queue. 
    '''
    worker_queue.put(job)

def get_job():
    '''
        Retrieves a job from the worker queue. This function will block until a job is available.
    '''
    return worker_queue.get()