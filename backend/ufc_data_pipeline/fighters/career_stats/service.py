"""
Recalculate fighter career stats from completed fight data via the main API service.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# Receives fight_id; returns nothing.
# Stub for slice 010 — real recalculation is wired in later slices.
def process_career_stats(fight_id: int) -> None:
    logger.info("Stub career stats process fight_id=%s", fight_id)
