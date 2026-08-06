"""Validate fight-stats Pub/Sub payloads and invoke the message processor."""

from __future__ import annotations

from typing import Any

from ufc_data_pipeline.fights.fight_stats.message_processor import (
    process_fight_stats_message,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url


def resolve_fight_stats_message(
    message_id: str,
    payload: dict[str, Any],
) -> DeliveryResult:
    """Validate domain fields and process one fight-stats delivery."""
    fight_id = _require_fight_id(payload)
    fight_url = _require_fight_url(payload)
    return process_fight_stats_message(message_id, fight_id, fight_url)


def _require_fight_id(payload: dict[str, Any]) -> int:
    if "fight_id" not in payload:
        raise PayloadValidationError("fight_id is required")
    fight_id = payload["fight_id"]
    if isinstance(fight_id, bool) or not isinstance(fight_id, int):
        raise PayloadValidationError("fight_id must be an integer")
    if fight_id <= 0:
        raise PayloadValidationError("fight_id must be a positive integer")
    return fight_id


def _require_fight_url(payload: dict[str, Any]) -> str:
    if "fight_url" not in payload:
        raise PayloadValidationError("fight_url is required")
    fight_url = normalize_ufcstats_url(str(payload["fight_url"]))
    if not fight_url:
        raise PayloadValidationError("fight_url is empty")
    return fight_url
