"""
Subscribe to Pub/Sub fighter profile jobs: scrape profile pages and update fighters.

Expects message JSON: ``{"fighter_id": <int>, "fighter_url": "<profile URL>"}``.

Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_FIGHTER_PROFILE_SUBSCRIPTION``.

All ``ack()`` / ``nack()`` calls happen only from the subscriber ``callback``, as Pub/Sub
requires.

TODO: Add dedicated fighter profile job status tracking improvements later,
owned by the fighter profile worker/service (e.g. stronger dedup/idempotency by fighter_id).
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

from ufc_data_pipeline.fighters.fighter_profile.config import (
    MAX_RETRY_COUNT,
    PROJECT_ID,
    SUBSCRIPTION_ID,
)
from ufc_data_pipeline.fighters.fighter_profile.service import process_fighter_profile
from ufc_data_pipeline.models import FighterProfileScrapeJob
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()


def _django_setup() -> None:
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


_django_ready = False


def ensure_django() -> None:
    """
    Initialize Django once before database access.
    Receives no parameters and returns nothing.
    """
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # #region agent log
    import time
    from pathlib import Path

    payload = {
        "sessionId": "d7790b",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    log_path = Path(__file__).resolve().parents[4] / "debug-d7790b.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")
    # #endregion


def parse_message_payload(raw: bytes) -> tuple[int, str]:
    """
    Parse the message payload into fighter_id and profile URL.
    Receives raw Pub/Sub bytes and returns fighter_id and fighter_url.
    """
    raw_text = raw.decode("utf-8")
    data = json.loads(raw_text)
    # #region agent log
    _debug_log(
        "A,B,C,D,E",
        "consumer.py:parse_message_payload",
        "parsed pubsub payload keys",
        {
            "raw_preview": raw_text[:500],
            "raw_len": len(raw_text),
            "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else type(data).__name__,
            "has_fighter_id": isinstance(data, dict) and "fighter_id" in data,
            "has_fighter_url": isinstance(data, dict) and "fighter_url" in data,
            "has_url": isinstance(data, dict) and "url" in data,
            "has_profile_url": isinstance(data, dict) and "profile_url" in data,
            "has_job_id": isinstance(data, dict) and "job_id" in data,
        },
    )
    # #endregion
    fighter_id = int(data["fighter_id"])
    fighter_url = str(data["fighter_url"]).strip()
    if not fighter_url:
        raise ValueError("fighter_url is empty")
    return fighter_id, fighter_url


def _get_or_create_job(fighter_id: int, fighter_url: str) -> FighterProfileScrapeJob | None:
    """
    Return a job row to process, or None when a scrape is already in progress.

    Reuses a RETRYING job; creates a new job when none is active (including after COMPLETED).
    Receives fighter_id and fighter_url; returns a job instance or None.
    """
    if FighterProfileScrapeJob.objects.filter(
        fighter_id=fighter_id,
        status=FighterProfileScrapeJob.Status.RUNNING,
    ).exists():
        return None

    retrying_job = (
        FighterProfileScrapeJob.objects.filter(
            fighter_id=fighter_id,
            status=FighterProfileScrapeJob.Status.RETRYING,
        )
        .order_by("-ran_at")
        .first()
    )
    if retrying_job is not None:
        retrying_job.status = FighterProfileScrapeJob.Status.RUNNING
        retrying_job.profile_url = fighter_url
        retrying_job.error_msg = ""
        retrying_job.save(update_fields=["status", "profile_url", "error_msg"])
        return retrying_job

    return FighterProfileScrapeJob.objects.create(
        fighter_id=fighter_id,
        profile_url=fighter_url,
        ran_at=timezone.now(),
        status=FighterProfileScrapeJob.Status.RUNNING,
        retry_count=0,
        error_msg="",
    )


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """
    Handle one fighter profile Pub/Sub message.
    Receives a Pub/Sub message and returns nothing.
    """
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    # #region agent log
    _debug_log(
        "C,D",
        "consumer.py:callback",
        "received pubsub message metadata",
        {
            "message_id": message.message_id,
            "ordering_key": message.ordering_key or "",
            "attributes": dict(message.attributes) if message.attributes else {},
            "data_len": len(message.data),
            "subscription": SUBSCRIPTION_ID,
            "project": PROJECT_ID,
        },
    )
    # #endregion

    # Try to parse the Pub/Sub payload before creating or loading a job row.
    try:
        fighter_id, fighter_url = parse_message_payload(message.data)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    job = _get_or_create_job(fighter_id, fighter_url)
    if job is None:
        logger.info(
            "Skipping fighter profile scrape; job already running fighter_id=%s",
            fighter_id,
        )
        message.ack()
        return

    # Try to scrape the profile page and update fighter metadata through the API service.
    try:
        process_fighter_profile(fighter_id, fighter_url)
        with transaction.atomic():
            job.status = FighterProfileScrapeJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        message.ack()
    except Exception as exc:
        err_text = str(exc)
        logger.exception(
            "Fighter profile scrape failed for job id=%s fighter_id=%s",
            job.pk,
            fighter_id,
        )
        job.retry_count += 1
        job.error_msg = err_text
        if job.retry_count >= MAX_RETRY_COUNT:
            job.status = FighterProfileScrapeJob.Status.FAILED
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.ack()
        else:
            job.status = FighterProfileScrapeJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.nack()


def run_subscriber() -> None:
    """
    Start the Pub/Sub subscriber for fighter profile jobs.
    Receives no parameters and returns nothing.
    """
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_FIGHTER_PROFILE_SUBSCRIPTION must be set."
        )

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info("Listening on %s", subscription_path)

    with subscriber:
        while True:
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
