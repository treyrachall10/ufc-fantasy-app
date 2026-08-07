"""
Run one Live Event Results Watcher pass and exit.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ufc_data_pipeline.fights.live_event_results.service import watch_live_event_results


class Command(BaseCommand):
    help = (
        "Watch the newest stored UFC event for live fight-result work; "
        "claim an event lease when needed and exit successfully on no-work paths."
    )

    def handle(self, *args, **options) -> None:
        try:
            result = watch_live_event_results()
        except Exception as exc:
            raise CommandError(f"Live Event Results Watcher failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Live Event Results Watcher completed "
                f"outcome={result.outcome.value} event_id={result.event_id}"
            )
        )
