"""
Consume Pub/Sub score-fight jobs and own their message/job lifecycle.

Expected JSON: ``{"fight_id": <positive int>}``.
Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_SCORE_FIGHT_SUBSCRIPTION``.
Only ``callback`` acknowledges or nacks messages.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import TimeoutError
from threading import Lock
from time import monotonic

from django.db import connection, transaction
from django.utils import timezone
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoringSourceUnscoreableError,
)
from ufc_data_pipeline.fantasy.score_fight.config import (
    MAX_MESSAGES,
    MAX_RETRY_COUNT,
    PROJECT_ID,
    SUBSCRIPTION_ID,
)
from ufc_data_pipeline.fantasy.score_fight.scoring import UnscoreableFightError
from ufc_data_pipeline.fantasy.score_fight.service import process_score_fight
from ufc_data_pipeline.models import ScoreFightJob
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = Lock()
_JOB_CLAIM_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()
_django_ready = False


def _django_setup() -> None:
    """Configure Django before accessing pipeline-owned job rows."""
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


def ensure_django() -> None:
    """Initialize Django once per worker process."""
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


def parse_message_payload(raw: bytes) -> int:
    """Parse a message containing one positive integer fight_id."""
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    fight_id = data["fight_id"]
    if isinstance(fight_id, bool) or not isinstance(fight_id, int):
        raise ValueError("fight_id must be an integer")
    if fight_id <= 0:
        raise ValueError("fight_id must be a positive integer")
    return fight_id


def _get_or_create_job(fight_id: int) -> ScoreFightJob | None:
    """Claim a new/retrying job; return None when the fight is already running."""
    # The local lock closes same-process absent-row races during the claim.
    with _JOB_CLAIM_LOCK, transaction.atomic():
        if connection.vendor == "postgresql":
            # The advisory lock closes the same race across worker instances.
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), %s)",
                    ["score_fight_job", fight_id],
                )

        if (
            ScoreFightJob.objects.select_for_update()
            .filter(
                fight_id=fight_id,
                status=ScoreFightJob.Status.RUNNING,
            )
            .exists()
        ):
            return None

        retrying_job = (
            ScoreFightJob.objects.select_for_update()
            .filter(
                fight_id=fight_id,
                status=ScoreFightJob.Status.RETRYING,
            )
            .order_by("-ran_at")
            .first()
        )
        if retrying_job is not None:
            retrying_job.status = ScoreFightJob.Status.RUNNING
            retrying_job.error_msg = ""
            retrying_job.save(update_fields=["status", "error_msg"])
            return retrying_job

        return ScoreFightJob.objects.create(
            fight_id=fight_id,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RUNNING,
            retry_count=0,
            error_msg="",
        )


def _mark_failed(job: ScoreFightJob, error: Exception) -> None:
    """Persist a terminal failure before its message is acknowledged."""
    with transaction.atomic():
        job.retry_count += 1
        job.status = ScoreFightJob.Status.FAILED
        job.error_msg = str(error)
        job.save(update_fields=["retry_count", "status", "error_msg"])


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Parse, claim, process, update status, then ack or nack one message."""
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()
    try:
        fight_id = parse_message_payload(message.data)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        # Invalid payloads cannot succeed on retry, so drop them.
        logger.warning("Invalid score-fight payload; acknowledging: %s", exc)
        message.ack()
        return

    job = _get_or_create_job(fight_id)
    if job is None:
        # Another RUNNING job owns this fight, so this delivery is redundant.
        logger.info("Skipping score-fight job already running fight_id=%s", fight_id)
        message.ack()
        return

    try:
        process_score_fight(fight_id)
        with transaction.atomic():
            job.status = ScoreFightJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        message.ack()
    except (ScoringSourceUnscoreableError, UnscoreableFightError) as exc:
        # Unscoreable outcomes are permanent, so fail once and do not redeliver.
        logger.warning(
            "Score-fight job is permanently unscoreable job_id=%s fight_id=%s: %s",
            job.pk,
            fight_id,
            exc,
        )
        _mark_failed(job, exc)
        message.ack()
    except Exception as exc:
        logger.exception(
            "Score-fight job failed job_id=%s fight_id=%s",
            job.pk,
            fight_id,
        )
        with transaction.atomic():
            job.retry_count += 1
            job.error_msg = str(exc)
            if job.retry_count >= MAX_RETRY_COUNT:
                # Exhausted failures are terminal, so save FAILED before ack.
                job.status = ScoreFightJob.Status.FAILED
            else:
                # Transient/incomplete failures retain the job and request redelivery.
                job.status = ScoreFightJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])

        if job.status == ScoreFightJob.Status.FAILED:
            message.ack()
        else:
            message.nack()


def run_subscriber() -> None:
    """Subscribe until the stream ends or shared idle settings request shutdown."""
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_SCORE_FIGHT_SUBSCRIPTION must be set."
        )

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
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
