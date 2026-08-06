"""
Subscribe to Pub/Sub career-stats jobs: track jobs and recalculate fighter career stats.

Expects message JSON: ``{"fight_id": <int>}``.

Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_CAREER_STATS_SUBSCRIPTION``.

All ``ack()`` / ``nack()`` calls happen only from the subscriber ``callback``, as Pub/Sub
requires.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import TimeoutError
from threading import Lock
from time import monotonic

from django.db import transaction
from django.utils import timezone
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from ufc_data_pipeline.fighters.career_stats.config import (
    MAX_MESSAGES,
    MAX_RETRY_COUNT,
    PROJECT_ID,
    SUBSCRIPTION_ID,
)
from ufc_data_pipeline.fighters.career_stats.service import (
    process_career_stats,
    publish_score_fight_job,
)
from ufc_data_pipeline.models import CareerStatsJob
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()


# Receives no parameters and returns nothing.
# This function configures Django so the consumer can read and write job rows.
def _django_setup() -> None:
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


_django_ready = False


# Receives no parameters and returns nothing.
# This function initializes Django once before database access.
def ensure_django() -> None:
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


# Receives raw Pub/Sub bytes and returns fight_id.
# This function validates the message payload before a job row is created.
def parse_message_payload(raw: bytes) -> int:
    data = json.loads(raw.decode("utf-8"))
    fight_id = int(data["fight_id"])
    if fight_id <= 0:
        raise ValueError("fight_id must be a positive integer")
    return fight_id


# Receives a Pub/Sub message and returns nothing.
# This function owns payload parse, job lifecycle, service invocation, and ack/nack.
def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    # Try to parse the Pub/Sub payload before creating or loading a job row.
    try:
        fight_id = parse_message_payload(message.data)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    job = claim_pubsub_job(
        model=CareerStatsJob,
        message_id=message.message_id,
        logical_filters={"fight_id": fight_id},
        create_kwargs={"fight_id": fight_id},
    )
    if job is None:
        message.ack()
        return

    # Try to recalculate career stats for fighters on the triggering fight.
    try:
        process_career_stats(fight_id)
        with transaction.atomic():
            job.status = CareerStatsJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        # Publish after the COMPLETED status commits so failures do not enqueue score-fight work.
        publish_score_fight_job(fight_id)
        message.ack()
    except Exception as exc:
        err_text = str(exc)
        logger.exception(
            "Career stats job failed for job id=%s fight_id=%s",
            job.pk,
            fight_id,
        )
        job.retry_count += 1
        job.error_msg = err_text
        if job.retry_count >= MAX_RETRY_COUNT:
            job.status = CareerStatsJob.Status.FAILED
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.ack()
        else:
            job.status = CareerStatsJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.nack()


# Receives no parameters and returns nothing.
# This function starts the career-stats subscriber and shuts down after idle timeout.
def run_subscriber() -> None:
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_CAREER_STATS_SUBSCRIPTION must be set."
        )

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    # Cap concurrent callbacks; same-fight_id dedup is enforced by job claims + DB constraints.
    flow_control = types.FlowControl(max_messages=MAX_MESSAGES)
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=callback,
        flow_control=flow_control,
    )
    logger.info(
        "Listening on %s (max_messages=%s)",
        subscription_path,
        MAX_MESSAGES,
    )

    with subscriber:
        # Loop until the streaming pull ends or idle shutdown cancels it.
        while True:
            # Try to wait for the next idle-check interval without ending the subscriber.
            try:
                streaming_pull_future.result(timeout=idle_check_interval_seconds())
                break
            except TimeoutError:
                with _STATE_LOCK:
                    idle_for_s = monotonic() - _LAST_MESSAGE_AT
                if should_shutdown_for_idle(idle_for_s):
                    logger.info(
                        "No messages for %.1fs; shutting down subscriber.",
                        idle_for_s,
                    )
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
