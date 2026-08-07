"""Validate fighter profile push payloads and invoke the message processor."""

from __future__ import annotations

from typing import Any

from ufc_data_pipeline.fighters.fighter_profile.message_processor import (
    process_fighter_profile_message,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


def resolve_fighter_profile_message(
    message_id: str,
    payload: dict[str, Any],
) -> DeliveryResult:
    """Validate required fields and delegate to the message processor."""
    if "fighter_id" not in payload:
        raise PayloadValidationError("fighter_id is required")
    if "fighter_url" not in payload:
        raise PayloadValidationError("fighter_url is required")

    try:
        fighter_id = int(payload["fighter_id"])
    except (TypeError, ValueError) as exc:
        raise PayloadValidationError("fighter_id must be an integer") from exc

    fighter_url = str(payload["fighter_url"]).strip()
    if not fighter_url:
        raise PayloadValidationError("fighter_url is empty")

    return process_fighter_profile_message(message_id, fighter_id, fighter_url)
