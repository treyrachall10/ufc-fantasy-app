"""Process career-stats Pub/Sub deliveries without transport ack/nack."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ufc_data_pipeline.fighters.career_stats.config import MAX_RETRY_COUNT
from ufc_data_pipeline.fighters.career_stats.service import (
    process_career_stats,
    publish_score_fight_job,
)
from ufc_data_pipeline.models import CareerStatsJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job

logger = logging.getLogger(__name__)


def process_career_stats_message(message_id: str, fight_id: int) -> DeliveryResult:
    """Claim work, recalculate career stats, and optionally publish score-fight."""
    job = claim_pubsub_job(
        model=CareerStatsJob,
        message_id=message_id,
        logical_filters={"fight_id": fight_id},
        create_kwargs={"fight_id": fight_id},
    )
    if job is None:
        return DeliveryResult.ACKNOWLEDGE

    try:
        process_career_stats(fight_id)
        with transaction.atomic():
            job.status = CareerStatsJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        publish_score_fight_job(fight_id)
        return DeliveryResult.ACKNOWLEDGE
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
            return DeliveryResult.ACKNOWLEDGE
        job.status = CareerStatsJob.Status.RETRYING
        job.save(update_fields=["retry_count", "error_msg", "status"])
        return DeliveryResult.RETRY
