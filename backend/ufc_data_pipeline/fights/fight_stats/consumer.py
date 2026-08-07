"""
Subscribe to Pub/Sub fight stats jobs: thin pull adapter over the shared resolver.

Expects message JSON: ``{"fight_id": <int>, "fight_url": "<fight detail URL>"}``.

Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_FIGHT_STATS_SUBSCRIPTION``.

All ``ack()`` / ``nack()`` calls happen only from the subscriber ``callback``, as Pub/Sub
requires.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import TimeoutError
from threading import Lock
from time import monotonic

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from ufc_data_pipeline.fights.fight_stats.api.resolver import resolve_fight_stats_message
from ufc_data_pipeline.fights.fight_stats.config import MAX_MESSAGES, PROJECT_ID, SUBSCRIPTION_ID
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

logger = logging.getLogger(__name__)

_STATE_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()


def _django_setup() -> None:
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


_django_ready = False


def ensure_django() -> None:
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Decode pull payload, resolve domain fields, and map DeliveryResult to ack/nack."""
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    try:
        payload = json.loads(message.data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise PayloadValidationError("payload must be a JSON object")
        result = resolve_fight_stats_message(message.message_id, payload)
    except (UnicodeDecodeError, json.JSONDecodeError, PayloadValidationError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return
    except Exception:
        logger.exception("Unexpected fight-stats pull callback failure")
        message.nack()
        return

    if result is DeliveryResult.RETRY:
        message.nack()
    else:
        message.ack()


def run_subscriber() -> None:
    ensure_django()
    if not PROJECT_ID or not SUBSCRIPTION_ID:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_FIGHT_STATS_SUBSCRIPTION must be set."
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
