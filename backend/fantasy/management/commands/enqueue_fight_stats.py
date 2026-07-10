"""
Enqueue a fight-stats Pub/Sub job.
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from fantasy.management.commands._pipeline_enqueue import (
    require_http_url,
    require_positive_int,
)
from ufc_data_pipeline.pubsub_publish import publish_json


class Command(BaseCommand):
    help = "Publish a fight-stats scrape job to Pub/Sub"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--fight-id", type=int, required=True)
        parser.add_argument("--fight-url", type=str, required=True)

    def handle(self, *args, **options) -> None:
        fight_id = require_positive_int("fight-id", options["fight_id"])
        fight_url = require_http_url("fight-url", options["fight_url"])
        topic_id = os.getenv("PUBSUB_FIGHT_STATS_TOPIC", "fight-stats-jobs")

        try:
            message_id = publish_json(
                topic_id,
                {"fight_id": fight_id, "fight_url": fight_url},
            )
        except Exception as exc:
            raise CommandError(f"Failed to publish fight stats job: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Published fight stats job message_id={message_id} "
                f"topic={topic_id} fight_id={fight_id}"
            )
        )
