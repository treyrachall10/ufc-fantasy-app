"""Validate score-fight payloads and invoke the message processor."""

from __future__ import annotations

from typing import Any

from ufc_data_pipeline.fantasy.score_fight.message_processor import (
    process_score_fight_message,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


def resolve_score_fight_message(
    message_id: str, payload: dict[str, Any]
) -> DeliveryResult:
    """Validate domain fields and run the score-fight processor."""
    if not isinstance(payload, dict):
        raise PayloadValidationError("payload must be a JSON object")
    fight_id = payload.get("fight_id")
    if fight_id is None:
        raise PayloadValidationError("fight_id is required")
    if isinstance(fight_id, bool) or not isinstance(fight_id, int):
        raise PayloadValidationError("fight_id must be an integer")
    if fight_id <= 0:
        raise PayloadValidationError("fight_id must be a positive integer")
    return process_score_fight_message(message_id, fight_id)
