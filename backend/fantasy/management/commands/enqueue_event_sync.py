"""
Run event page sync (discover new events and enqueue fight-import jobs).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ufc_data_pipeline.events.event_page_sync.service import sync_event_page


class Command(BaseCommand):
    help = "Sync completed UFC events and publish fights-in-event jobs for new rows"

    def handle(self, *args, **options) -> None:
        try:
            job, created = sync_event_page()
        except Exception as exc:
            raise CommandError(f"Event sync failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Event sync completed job_id={job.pk} status={job.status} "
                f"new_events={len(created)}"
            )
        )
