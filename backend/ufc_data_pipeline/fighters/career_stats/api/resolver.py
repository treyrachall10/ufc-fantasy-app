"""Validate career-stats payloads and invoke the message processor."""

from __future__ import annotations

from typing import Any

from ufc_data_pipeline.fighters.career_stats.message_processor import (
    process_career_stats_message,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


def resolve_career_stats_message(
    message_id: str, payload: dict[str, Any]
) -> DeliveryResult:
    """Validate domain fields and run the career-stats processor."""
    fight_id = _require_positive_int(payload.get("fight_id"), "fight_id")
    return process_career_stats_message(message_id, fight_id)


def _require_positive_int(value: object, field_name: str) -> int:
    if value is None:
        raise PayloadValidationError(f"{field_name} is required")
    if isinstance(value, bool):
        raise PayloadValidationError(f"{field_name} must be an integer, not bool")
    if not isinstance(value, int):
        raise PayloadValidationError(f"{field_name} must be an integer")
    if value <= 0:
        raise PayloadValidationError(f"{field_name} must be a positive integer")
    return value
