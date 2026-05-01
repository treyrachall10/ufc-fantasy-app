import threading
from django.core.management.base import BaseCommand
from image_worker_service.downloader import consume_jobs
from athlete_image_service.scrape_fighter_images import scrape_fighter_images_df

class Command(BaseCommand):
    """
        -   Creates the custom command to update athlete images
    """
    help = "Updates athlete images in the database"

    def handle(self, *args, **options):
        scrape_fighter_images_df()