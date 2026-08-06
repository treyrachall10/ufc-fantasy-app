"""Transport-agnostic score-fight Pub/Sub message processing."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoringSourceUnscoreableError,
)
from ufc_data_pipeline.fantasy.score_fight.config import MAX_RETRY_COUNT
from ufc_data_pipeline.fantasy.score_fight.scoring import UnscoreableFightError
from ufc_data_pipeline.fantasy.score_fight.service import process_score_fight
from ufc_data_pipeline.models import ScoreFightJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job

logger = logging.getLogger(__name__)


def _mark_failed(job: ScoreFightJob, error: Exception) -> None:
    """Persist a terminal failure before its message is acknowledged."""
    with transaction.atomic():
        job.retry_count += 1
        job.status = ScoreFightJob.Status.FAILED
        job.error_msg = str(error)
        job.save(update_fields=["retry_count", "status", "error_msg"])


def process_score_fight_message(message_id: str, fight_id: int) -> DeliveryResult:
    """
    Claim a score-fight job, score the fight, and return delivery outcome.

    Returns ``ACKNOWLEDGE`` for success, dedupe skips, unscoreable fights, and
    terminal failure; ``RETRY`` for retryable failures below ``MAX_RETRY_COUNT``.
    """
    job = claim_pubsub_job(
        model=ScoreFightJob,
        message_id=message_id,
        logical_filters={"fight_id": fight_id},
        create_kwargs={"fight_id": fight_id},
    )
    if job is None:
        return DeliveryResult.ACKNOWLEDGE

    try:
        process_score_fight(fight_id)
        with transaction.atomic():
            job.status = ScoreFightJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        return DeliveryResult.ACKNOWLEDGE
    except (ScoringSourceUnscoreableError, UnscoreableFightError) as exc:
        logger.warning(
            "Score-fight job is permanently unscoreable job_id=%s fight_id=%s: %s",
            job.pk,
            fight_id,
            exc,
        )
        _mark_failed(job, exc)
        return DeliveryResult.ACKNOWLEDGE
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
                job.status = ScoreFightJob.Status.FAILED
            else:
                job.status = ScoreFightJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])

        if job.status == ScoreFightJob.Status.FAILED:
            return DeliveryResult.ACKNOWLEDGE
        return DeliveryResult.RETRY
