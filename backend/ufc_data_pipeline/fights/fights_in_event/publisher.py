"""Publish downstream work after fights-in-event reconciliation commits."""

from __future__ import annotations

import logging

from ufc_data_pipeline.fights.fights_in_event.config import (
    FIGHTER_PROFILE_TOPIC_ID,
    PROJECT_ID,
)
from ufc_data_pipeline.pubsub_publish import publish_json
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

logger = logging.getLogger(__name__)


def publish_fighter_profile_job(fighter_id: int, fighter_url: str) -> str:
    """Publish one required new/missing fighter-profile handoff."""
    normalized_url = normalize_ufcstats_url(fighter_url)
    if not normalized_url:
        raise ValueError(f"fighter_url is empty for fighter_id={fighter_id}")
    message_id = publish_json(
        FIGHTER_PROFILE_TOPIC_ID,
        {"fighter_id": fighter_id, "fighter_url": normalized_url},
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published fighter-profile job fighter_id=%s message_id=%s",
        fighter_id,
        message_id,
    )
    return message_id
