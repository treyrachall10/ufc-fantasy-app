"""
Subscribe to Pub/Sub fight stats jobs: track jobs and process fight detail scrapes.

Expects message JSON: ``{"fight_id": <int>, "fight_url": "<fight detail URL>"}``.

Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_FIGHT_STATS_SUBSCRIPTION``.

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

from ufc_data_pipeline.fights.fight_stats.config import (
    MAX_MESSAGES,
    MAX_RETRY_COUNT,
    PROJECT_ID,
    SUBSCRIPTION_ID,
)
from ufc_data_pipeline.fights.fight_stats.service import (
    process_fight_stats,
    publish_career_stats_job,
)
from ufc_data_pipeline.models import FightStatsScrapeJob
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url
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


# Receives raw Pub/Sub bytes and returns fight_id and fight_url.
# This function validates the message payload before a job row is created.
def parse_message_payload(raw: bytes) -> tuple[int, str]:
    data = json.loads(raw.decode("utf-8"))
    fight_id = int(data["fight_id"])
    fight_url = normalize_ufcstats_url(str(data["fight_url"]))
    if not fight_url:
        raise ValueError("fight_url is empty")
    return fight_id, fight_url


# Receives fight_id, fight_url, and message_id; returns a job instance or None.
# This function claims work under row locks / constraints so duplicates cannot double-scrape.
def _get_or_create_job(
    fight_id: int, fight_url: str, message_id: str
) -> FightStatsScrapeJob | None:
    return claim_pubsub_job(
        model=FightStatsScrapeJob,
        message_id=message_id,
        logical_filters={"fight_id": fight_id},
        create_kwargs={"fight_id": fight_id, "fight_url": fight_url},
        retry_update_fields={"fight_url": fight_url},
    )


# Receives a Pub/Sub message and returns nothing.
# This function owns payload parse, job lifecycle, scrape invocation, and ack/nack.
def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    # Try to parse the Pub/Sub payload before creating or loading a job row.
    try:
        fight_id, fight_url = parse_message_payload(message.data)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    job = _get_or_create_job(fight_id, fight_url, message.message_id)
    if job is None:
        message.ack()
        return

    # Try to scrape the fight page and upsert stats through the API service.
    try:
        process_fight_stats(fight_id, fight_url)
        with transaction.atomic():
            job.status = FightStatsScrapeJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        # Publish after the COMPLETED status commits so failures do not enqueue career-stats work.
        publish_career_stats_job(fight_id)
        message.ack()
    except Exception as exc:
        err_text = str(exc)
        logger.exception(
            "Fight stats scrape failed for job id=%s fight_id=%s",
            job.pk,
            fight_id,
        )
        job.retry_count += 1
        job.error_msg = err_text
        if job.retry_count >= MAX_RETRY_COUNT:
            job.status = FightStatsScrapeJob.Status.FAILED
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.ack()
        else:
            job.status = FightStatsScrapeJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.nack()


# Receives no parameters and returns nothing.
# This function starts the fight stats subscriber and shuts down after idle timeout.
def run_subscriber() -> None:
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_FIGHT_STATS_SUBSCRIPTION must be set."
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
