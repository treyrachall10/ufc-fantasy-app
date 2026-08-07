"""
Enqueue a fighter-profile Pub/Sub job.
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
    help = "Publish a fighter-profile scrape job to Pub/Sub"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--fighter-id", type=int, required=True)
        parser.add_argument("--fighter-url", type=str, required=True)

    def handle(self, *args, **options) -> None:
        fighter_id = require_positive_int("fighter-id", options["fighter_id"])
        fighter_url = require_http_url("fighter-url", options["fighter_url"])
        topic_id = os.getenv("PUBSUB_FIGHTER_PROFILE_TOPIC", "fighter-profile-jobs")

        try:
            message_id = publish_json(
                topic_id,
                {"fighter_id": fighter_id, "fighter_url": fighter_url},
            )
        except Exception as exc:
            raise CommandError(f"Failed to publish fighter profile job: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Published fighter profile job message_id={message_id} "
                f"topic={topic_id} fighter_id={fighter_id}"
            )
        )
