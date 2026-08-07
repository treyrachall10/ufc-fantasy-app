"""Publish Fights In Event jobs to Pub/Sub."""

from __future__ import annotations

import logging
import os

from ufc_data_pipeline.pubsub_publish import publish_json

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
FIGHTS_IN_EVENT_TOPIC_ID = os.getenv("PUBSUB_FIGHTS_IN_EVENT_TOPIC", "fights-in-event")


def publish_fights_in_event(
    event_id: int,
    event_url: str,
    *,
    reason: str | None = None,
    fingerprint: str | None = None,
) -> str:
    """
    Publish one fights-in-event message.

    Required fields remain ``event_id`` and ``url``. Optional ``reason`` and
    ``fingerprint`` are backward-compatible metadata for logging.
    """
    url = (event_url or "").strip()
    if not url:
        raise ValueError(f"event_url is empty for event_id={event_id}")
    payload: dict = {"url": url, "event_id": event_id}
    if reason:
        payload["reason"] = reason
    if fingerprint:
        payload["fingerprint"] = fingerprint
    message_id = publish_json(
        FIGHTS_IN_EVENT_TOPIC_ID,
        payload,
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published fights-in-event event_id=%s url=%s reason=%s fingerprint=%s "
        "message_id=%s",
        event_id,
        url,
        reason,
        fingerprint,
        message_id,
    )
    return message_id
