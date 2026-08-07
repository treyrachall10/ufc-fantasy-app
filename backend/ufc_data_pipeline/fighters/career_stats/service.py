"""
Recalculate fighter career stats from completed fight data via the main API service.
"""

from __future__ import annotations

import logging

from ufc_data_pipeline.fighters.career_stats import api_client
from ufc_data_pipeline.fighters.career_stats.config import (
    PROJECT_ID,
    SCORE_FIGHT_TOPIC_ID,
)
from ufc_data_pipeline.fighters.career_stats.counters import calculate_career_stats
from ufc_data_pipeline.pubsub_publish import publish_json

logger = logging.getLogger(__name__)


# Receives fight_id; returns nothing; raises on failure.
# Loads CareerStatsSource, recalculates both fighters, and upserts each career-stats row.
def process_career_stats(fight_id: int) -> None:
    logger.info("Started career stats job fight_id=%s", fight_id)

    source = api_client.fetch_career_stats_source(fight_id)
    fighters = source.get("fighters") or []
    if not fighters:
        raise RuntimeError(
            f"CareerStatsSource returned no fighters for fight_id={fight_id}"
        )

    # Recalculate and upsert career stats for each fighter on the triggering fight.
    for fighter_payload in fighters:
        fighter_id = fighter_payload.get("fighter_id")
        if fighter_id is None:
            raise RuntimeError(
                f"CareerStatsSource fighter payload missing fighter_id "
                f"for fight_id={fight_id}"
            )
        fights = fighter_payload.get("fights") or []
        values = calculate_career_stats(int(fighter_id), fights)
        api_client.upsert_fighter_career_stats(int(fighter_id), values)
        logger.info(
            "Upserted career stats fighter_id=%s fight_id=%s total_fights=%s",
            fighter_id,
            fight_id,
            values.get("total_fights"),
        )

    logger.info("Completed career stats job fight_id=%s", fight_id)


# Receives a fight_id and returns the Pub/Sub message id.
# Publishes the score-fight handoff after a successful career-stats recalculation.
def publish_score_fight_job(fight_id: int) -> str:
    message_id = publish_json(
        SCORE_FIGHT_TOPIC_ID,
        {"fight_id": fight_id},
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published score-fight job fight_id=%s topic=%s message_id=%s",
        fight_id,
        SCORE_FIGHT_TOPIC_ID,
        message_id,
    )
    return message_id
