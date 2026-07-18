"""
Run one Event Watcher discovery pass and exit.
"""

from __future__ import annotations

import argparse
from datetime import date as Date
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from ufc_data_pipeline.events.event_watcher.service import watch_events


def _iso_date(value: str) -> Date:
    """Parse a strict ``YYYY-MM-DD`` CLI value before any work begins."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--backfill-from must be an ISO date (YYYY-MM-DD); got {value!r}"
        ) from exc


class Command(BaseCommand):
    help = (
        "Discover new completed UFC events via API + listing scrape; "
        "exit successfully when there is no work. With --backfill-from, replay "
        "every listing event on or after an inclusive date through the normal "
        "downstream pipeline."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--backfill-from",
            dest="backfill_from",
            type=_iso_date,
            default=None,
            metavar="YYYY-MM-DD",
            help=(
                "Replay every completed-listing event on or after this "
                "inclusive date instead of processing unknown events only."
            ),
        )

    def handle(self, *args, **options) -> None:
        backfill_from: Date | None = options.get("backfill_from")
        try:
            job, processed = watch_events(backfill_from=backfill_from)
        except Exception as exc:
            raise CommandError(f"Event watcher failed: {exc}") from exc

        mode = "backfill" if backfill_from else "normal"
        self.stdout.write(
            self.style.SUCCESS(
                f"Event watcher completed job_id={job.pk} status={job.status} "
                f"mode={mode} processed_events={len(processed)}"
            )
        )
