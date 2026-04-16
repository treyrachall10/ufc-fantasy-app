import queue

worker_queue = queue.Queue()

def publish_job(job):
    worker_queue.put(job)

def get_job():
    return worker_queue.get()