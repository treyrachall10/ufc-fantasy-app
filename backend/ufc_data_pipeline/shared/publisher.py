"""Shared Pub/Sub publishers used by multiple pipeline stages."""

from __future__ import annotations

import logging
import os

from ufc_data_pipeline.pubsub_publish import publish_json
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
FIGHT_STATS_TOPIC_ID = os.getenv("PUBSUB_FIGHT_STATS_TOPIC", "fight-stats-jobs")


def publish_fight_stats_job(fight_id: int, fight_url: str) -> str:
    """Publish one completed fight to the existing fight-stats topic."""
    normalized_url = normalize_ufcstats_url(fight_url)
    if not normalized_url:
        raise ValueError(f"fight_url is empty for fight_id={fight_id}")
    message_id = publish_json(
        FIGHT_STATS_TOPIC_ID,
        {"fight_id": fight_id, "fight_url": normalized_url},
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published fight-stats job fight_id=%s message_id=%s",
        fight_id,
        message_id,
    )
    return message_id
