"""
Publish fights-in-event handoff messages from the Event Watcher.
"""

from __future__ import annotations

import logging

from ufc_data_pipeline.events.event_watcher.config import (
    FIGHTS_IN_EVENT_TOPIC_ID,
    PROJECT_ID,
)
from ufc_data_pipeline.pubsub_publish import publish_json

logger = logging.getLogger(__name__)


def publish_fights_in_event(event_id: int, event_url: str) -> str:
    """
    Publish one fights-in-event message after a successful Event upsert.
    Receives event_id and event_url; returns the Pub/Sub message id.
    """
    message_id = publish_json(
        FIGHTS_IN_EVENT_TOPIC_ID,
        {"url": event_url, "event_id": event_id},
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published fights-in-event event_id=%s url=%s message_id=%s",
        event_id,
        event_url,
        message_id,
    )
    return message_id
