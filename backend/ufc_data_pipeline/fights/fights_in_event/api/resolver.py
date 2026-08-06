"""
Validate fights-in-event Pub/Sub payloads and invoke the message processor.
"""

from __future__ import annotations

import logging
from typing import Any

from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError

from ..message_processor import process_fights_in_event_message

logger = logging.getLogger(__name__)


def resolve_fights_in_event_message(
    message_id: str,
    payload: dict[str, Any],
) -> DeliveryResult:
    """
    Validate required payload fields and delegate to the message processor.
    """
    if "url" not in payload:
        raise PayloadValidationError("url is required")
    url_raw = payload["url"]
    if not isinstance(url_raw, str):
        raise PayloadValidationError("url must be a string")
    url = url_raw.strip()
    if not url:
        raise PayloadValidationError("url is empty")

    if "event_id" not in payload:
        raise PayloadValidationError("event_id is required")
    try:
        event_id = int(payload["event_id"])
    except (TypeError, ValueError) as exc:
        raise PayloadValidationError("event_id must be an integer") from exc

    reason = payload.get("reason")
    fingerprint = payload.get("fingerprint")
    if reason or fingerprint:
        logger.info(
            "fights_in_event payload metadata event_id=%s reason=%s fingerprint=%s",
            event_id,
            reason,
            fingerprint,
        )

    return process_fights_in_event_message(message_id, url, event_id)
