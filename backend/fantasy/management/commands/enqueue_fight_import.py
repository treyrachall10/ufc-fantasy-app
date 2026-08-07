"""
Enqueue a fights-in-event Pub/Sub job.
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
    help = "Publish a fights-in-event job to Pub/Sub"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--event-id", type=int, required=True)
        parser.add_argument("--url", type=str, required=True)

    def handle(self, *args, **options) -> None:
        event_id = require_positive_int("event-id", options["event_id"])
        url = require_http_url("url", options["url"])
        topic_id = os.getenv("PUBSUB_FIGHTS_IN_EVENT_TOPIC", "fights-in-event")

        try:
            message_id = publish_json(
                topic_id,
                {"url": url, "event_id": event_id},
            )
        except Exception as exc:
            raise CommandError(f"Failed to publish fight import job: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Published fight import job message_id={message_id} "
                f"topic={topic_id} event_id={event_id}"
            )
        )
