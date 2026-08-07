"""
Process fight-stats Pub/Sub deliveries and return transport outcomes.

Claim, scrape, status updates, and downstream career-stats publish live here.
Transport adapters map ``DeliveryResult`` to ack/nack or HTTP status codes.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ufc_data_pipeline.fights.fight_stats.config import MAX_RETRY_COUNT
from ufc_data_pipeline.fights.fight_stats.service import (
    process_fight_stats,
    publish_career_stats_job,
)
from ufc_data_pipeline.models import FightStatsScrapeJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job

logger = logging.getLogger(__name__)


def process_fight_stats_message(
    message_id: str,
    fight_id: int,
    fight_url: str,
) -> DeliveryResult:
    """Claim one delivery, scrape fight stats, and return ack vs retry."""
    job = claim_pubsub_job(
        model=FightStatsScrapeJob,
        message_id=message_id,
        logical_filters={"fight_id": fight_id},
        create_kwargs={"fight_id": fight_id, "fight_url": fight_url},
        retry_update_fields={"fight_url": fight_url},
    )
    if job is None:
        return DeliveryResult.ACKNOWLEDGE

    try:
        process_fight_stats(fight_id, fight_url)
        with transaction.atomic():
            job.status = FightStatsScrapeJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        publish_career_stats_job(fight_id)
        return DeliveryResult.ACKNOWLEDGE
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
            return DeliveryResult.ACKNOWLEDGE
        job.status = FightStatsScrapeJob.Status.RETRYING
        job.save(update_fields=["retry_count", "error_msg", "status"])
        return DeliveryResult.RETRY
