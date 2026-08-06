"""Transport-agnostic fighter profile Pub/Sub message processing."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ufc_data_pipeline.fighters.fighter_profile.config import MAX_RETRY_COUNT
from ufc_data_pipeline.fighters.fighter_profile.service import process_fighter_profile
from ufc_data_pipeline.models import FighterProfileScrapeJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job

logger = logging.getLogger(__name__)


def process_fighter_profile_message(
    message_id: str,
    fighter_id: int,
    fighter_url: str,
) -> DeliveryResult:
    """
    Claim a fighter profile scrape job, scrape, and update delivery outcome.

    Returns ``ACKNOWLEDGE`` for success, dedupe skips, and terminal failure;
    ``RETRY`` for retryable failures below ``MAX_RETRY_COUNT``.
    """
    job = claim_pubsub_job(
        model=FighterProfileScrapeJob,
        message_id=message_id,
        logical_filters={"fighter_id": fighter_id},
        create_kwargs={"fighter_id": fighter_id, "profile_url": fighter_url},
        retry_update_fields={"profile_url": fighter_url},
    )
    if job is None:
        return DeliveryResult.ACKNOWLEDGE

    try:
        process_fighter_profile(fighter_id, fighter_url)
        with transaction.atomic():
            job.status = FighterProfileScrapeJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])
        return DeliveryResult.ACKNOWLEDGE
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
            return DeliveryResult.ACKNOWLEDGE

        job.status = FighterProfileScrapeJob.Status.RETRYING
        job.save(update_fields=["retry_count", "error_msg", "status"])
        return DeliveryResult.RETRY
