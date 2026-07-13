"""
Enqueue a career-stats Pub/Sub job.
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from fantasy.management.commands._pipeline_enqueue import require_positive_int
from ufc_data_pipeline.pubsub_publish import publish_json


class Command(BaseCommand):
    help = "Publish a career-stats recalculation job to Pub/Sub"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--fight-id", type=int, required=True)

    def handle(self, *args, **options) -> None:
        fight_id = require_positive_int("fight-id", options["fight_id"])
        topic_id = os.getenv("PUBSUB_CAREER_STATS_TOPIC", "career-stats-jobs")

        try:
            message_id = publish_json(
                topic_id,
                {"fight_id": fight_id},
            )
        except Exception as exc:
            raise CommandError(f"Failed to publish career stats job: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Published career stats job message_id={message_id} "
                f"topic={topic_id} fight_id={fight_id}"
            )
        )
