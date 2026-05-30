"""
Create fighter profile scrape jobs and publish them to Pub/Sub.
"""

from __future__ import annotations

import json
import logging

from django.utils import timezone
from google.cloud import pubsub_v1

from fantasy.models import Fighters
from ufc_data_pipeline.fighters.fighter_profile.config import (
    DUPLICATE_BLOCK_STATUSES,
    PROJECT_ID,
    TOPIC_ID,
)
from ufc_data_pipeline.models import FighterProfileScrapeJob

logger = logging.getLogger(__name__)


def has_active_profile_job(fighter_id: int) -> bool:
    """
    Return True when a non-failed fighter profile job already exists.
    Receives a fighter_id and returns whether enqueue should be skipped.
    """
    return FighterProfileScrapeJob.objects.filter(
        fighter_id=fighter_id,
        status__in=DUPLICATE_BLOCK_STATUSES,
    ).exists()


def enqueue_fighter_profile_sync(fighter: Fighters) -> FighterProfileScrapeJob | None:
    """
    Create a fighter profile scrape job and publish it to Pub/Sub.
    Receives a Fighters instance and returns the created job or None when skipped.
    """
    profile_url = (fighter.profile_url or "").strip()
    if not profile_url:
        return None
    if not PROJECT_ID or not TOPIC_ID:
        logger.warning(
            "Skipping fighter profile enqueue; Pub/Sub env is not configured fighter_id=%s",
            fighter.fighter_id,
        )
        return None
    if has_active_profile_job(fighter.fighter_id):
        logger.info(
            "Skipping duplicate fighter profile job fighter_id=%s",
            fighter.fighter_id,
        )
        return None

    job = FighterProfileScrapeJob.objects.create(
        fighter_id=fighter.fighter_id,
        profile_url=profile_url,
        ran_at=timezone.now(),
        status=FighterProfileScrapeJob.Status.PENDING,
        retry_count=0,
        error_msg="",
    )

    # Try to publish the job message after the database row is created.
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
        publisher.publish(
            topic_path,
            json.dumps(
                {
                    "job_id": job.pk,
                    "fighter_id": fighter.fighter_id,
                    "url": profile_url,
                }
            ).encode("utf-8"),
        )
    except Exception:
        logger.exception(
            "Failed to publish fighter profile job fighter_id=%s job_id=%s",
            fighter.fighter_id,
            job.pk,
        )
        job.status = FighterProfileScrapeJob.Status.FAILED
        job.error_msg = "Failed to publish Pub/Sub message"
        job.save(update_fields=["status", "error_msg"])
        return job

    return job
