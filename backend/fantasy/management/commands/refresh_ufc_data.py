from django.core.management.base import BaseCommand, CommandError
from scripts.scrape.scrape_ufc_stats_unparsed_data import scrape_stats
from scripts.parse_data import parse_all_data
from scripts.db_population import populate_database

class Command(BaseCommand):
    """
        -   Creates the custom command to update ufc stats and the database
    """
    help = "Updates ufc stats csv's and database tables"

    def handle(self, *args, **options):
        scrape_stats()
        parse_all_data()
        populate_database()