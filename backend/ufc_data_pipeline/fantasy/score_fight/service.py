"""Coordinate score-fight source loading, calculation, and persistence."""

from __future__ import annotations

import logging

from ufc_data_pipeline.fantasy.score_fight import api_client
from ufc_data_pipeline.fantasy.score_fight.scoring import calculate_fight_scoring

logger = logging.getLogger(__name__)


def process_score_fight(fight_id: int) -> None:
    """Load, calculate, and persist the complete score state for one fight."""
    logger.info("Started score-fight job fight_id=%s", fight_id)
    source = api_client.fetch_scoring_source(fight_id)
    score_payload = calculate_fight_scoring(source)
    api_client.set_fight_scoring(fight_id, score_payload)
    logger.info("Completed score-fight job fight_id=%s", fight_id)
