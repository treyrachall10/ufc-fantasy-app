"""
Run one Event Watcher discovery pass and exit.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ufc_data_pipeline.events.event_watcher.service import watch_events


class Command(BaseCommand):
    help = (
        "Discover new completed UFC events via API + listing scrape; "
        "exit successfully when there is no work"
    )

    def handle(self, *args, **options) -> None:
        try:
            job, unknown = watch_events()
        except Exception as exc:
            raise CommandError(f"Event watcher failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Event watcher completed job_id={job.pk} status={job.status} "
                f"unknown_events={len(unknown)}"
            )
        )
