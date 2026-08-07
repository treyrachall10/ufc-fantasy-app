"""
Shared Pub/Sub JSON publish helper for pipeline stages and management commands.
"""

from __future__ import annotations

import json
import os
from typing import Any

from google.cloud import pubsub_v1


def publish_json(
    topic_id: str,
    payload: dict[str, Any],
    *,
    project_id: str | None = None,
) -> str:
    """
    Publish a JSON object to a Pub/Sub topic and return the message id.

    Uses ``GOOGLE_CLOUD_PROJECT`` when ``project_id`` is omitted. Relies on
    ``PUBSUB_EMULATOR_HOST`` (or GCP credentials) from the environment.
    """
    resolved_project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not resolved_project:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set")
    if not topic_id or not str(topic_id).strip():
        raise ValueError("topic_id must be a non-empty string")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(resolved_project, topic_id)
    future = publisher.publish(
        topic_path,
        json.dumps(payload).encode("utf-8"),
    )
    return future.result()
