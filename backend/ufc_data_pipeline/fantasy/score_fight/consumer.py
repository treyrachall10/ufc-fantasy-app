"""
Consume Pub/Sub score-fight jobs and own their message/job lifecycle.

Expected JSON: ``{"fight_id": <positive int>}``.
Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_SCORE_FIGHT_SUBSCRIPTION``.
Only ``callback`` acknowledges or nacks messages.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import TimeoutError
from threading import Lock
from time import monotonic

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from ufc_data_pipeline.fantasy.score_fight.api.resolver import (
    resolve_score_fight_message,
)
from ufc_data_pipeline.fantasy.score_fight.config import (
    MAX_MESSAGES,
    PROJECT_ID,
    SUBSCRIPTION_ID,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()
_django_ready = False


def _django_setup() -> None:
    """Configure Django before accessing pipeline-owned job rows."""
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


def ensure_django() -> None:
    """Initialize Django once per worker process."""
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Decode payload, delegate to resolver, then ack or nack one message."""
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    try:
        payload = json.loads(message.data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise PayloadValidationError("payload must be a JSON object")
        result = resolve_score_fight_message(message.message_id, payload)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        PayloadValidationError,
        TypeError,
    ) as exc:
        logger.warning("Invalid score-fight payload; acknowledging: %s", exc)
        message.ack()
        return
    except Exception:
        logger.exception("Unexpected error in score-fight pull callback")
        message.nack()
        return

    if result is DeliveryResult.RETRY:
        message.nack()
    else:
        message.ack()


def run_subscriber() -> None:
    """Subscribe until the stream ends or shared idle settings request shutdown."""
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_SCORE_FIGHT_SUBSCRIPTION must be set."
        )

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    flow_control = types.FlowControl(max_messages=MAX_MESSAGES)
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=callback,
        flow_control=flow_control,
    )
    logger.info(
        "Listening on %s (max_messages=%s)",
        subscription_path,
        MAX_MESSAGES,
    )

    with subscriber:
        while True:
            try:
                streaming_pull_future.result(timeout=idle_check_interval_seconds())
                break
            except TimeoutError:
                with _STATE_LOCK:
                    idle_for_s = monotonic() - _LAST_MESSAGE_AT
                if should_shutdown_for_idle(idle_for_s):
                    logger.info(
                        "No messages for %.1fs; shutting down subscriber.",
                        idle_for_s,
                    )
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
