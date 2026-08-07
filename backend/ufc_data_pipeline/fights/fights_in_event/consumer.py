"""
Subscribe to Pub/Sub fight-in-event jobs: thin transport adapter over resolver/processor.

Expects message JSON: ``{"url": "<event page URL>", "event_id": <int>}``.

Environment: ``GOOGLE_CLOUD_PROJECT``, ``PUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION``.

All ``ack()`` / ``nack()`` calls happen only from the subscriber ``callback``, as Pub/Sub
requires.
"""

from __future__ import annotations

import json
import logging
import os
from threading import Lock
from time import monotonic
from concurrent.futures import TimeoutError

import requests
from bs4 import BeautifulSoup
from google.cloud import pubsub_v1

from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    should_shutdown_for_idle,
)

from .api.resolver import resolve_fights_in_event_message

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
subscription_id = os.getenv("PUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION")
_STATE_LOCK = Lock()
_LAST_MESSAGE_AT = monotonic()


def _django_setup() -> None:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
    django.setup()


_django_ready = False


def ensure_django() -> None:
    global _django_ready
    if not _django_ready:
        _django_setup()
        _django_ready = True


def fetch_soup(url: str) -> BeautifulSoup:
    """
    Fetch the soup from the event page.
    """
    response = requests.get(url, timeout=_REQUEST_TIMEOUT_S)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """
    Callback function to handle the message from Pub/Sub.
    """
    global _LAST_MESSAGE_AT
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic()

    ensure_django()

    try:
        payload = json.loads(message.data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    try:
        result = resolve_fights_in_event_message(message.message_id, payload)
    except PayloadValidationError as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    if result == DeliveryResult.ACKNOWLEDGE:
        message.ack()
    else:
        message.nack()


def run_subscriber() -> None:
    """
        Starts the subscriber to listen for messages on Pub/Sub subscription.
    """

    ensure_django()
    if not project_id or not subscription_id:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT and PUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION must be set."
        )

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info("Listening on %s", subscription_path)

    with subscriber:
        while True:
            try:
                streaming_pull_future.result(timeout=idle_check_interval_seconds())
                break
            except TimeoutError:
                with _STATE_LOCK:
                    idle_for_s = monotonic() - _LAST_MESSAGE_AT
                if should_shutdown_for_idle(idle_for_s):
                    logger.info("No messages for %.1fs; shutting down subscriber.", idle_for_s)
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
