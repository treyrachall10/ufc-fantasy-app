"""
Ensure local Pub/Sub emulator topics and subscriptions exist.
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError
from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1


# topic_id -> subscription_id (None = topic only)
_RESOURCES: list[tuple[str, str | None]] = [
    ("image-jobs", "image-worker-sub"),
    ("fights-in-event", "fights-in-event-sub"),
    ("fighter-profile-jobs", "fighter-profile-jobs-sub"),
    ("fight-stats-jobs", "fight-stats-jobs-sub"),
    ("career-stats-jobs", "career-stats-jobs-sub"),
    ("score-fight-jobs", "score-fight-jobs-sub"),
]


class Command(BaseCommand):
    help = "Create Pub/Sub emulator topics/subscriptions if missing (idempotent)"

    def handle(self, *args, **options) -> None:
        if not os.getenv("PUBSUB_EMULATOR_HOST"):
            raise CommandError(
                "PUBSUB_EMULATOR_HOST must be set (e.g. pubsub:8085 inside Compose)"
            )

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        for topic_id, subscription_id in _RESOURCES:
            topic_path = publisher.topic_path(project_id, topic_id)
            try:
                publisher.create_topic(request={"name": topic_path})
                self.stdout.write(f"Created topic {topic_id}")
            except AlreadyExists:
                self.stdout.write(f"Topic already exists: {topic_id}")

            if not subscription_id:
                continue

            sub_path = subscriber.subscription_path(project_id, subscription_id)
            try:
                subscriber.create_subscription(
                    request={"name": sub_path, "topic": topic_path}
                )
                self.stdout.write(f"Created subscription {subscription_id}")
            except AlreadyExists:
                self.stdout.write(f"Subscription already exists: {subscription_id}")

        self.stdout.write(self.style.SUCCESS("Pub/Sub emulator resources ready"))
