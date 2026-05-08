"""
Subscribe to Pub/Sub fight-in-event jobs: fetch event HTML, parse fights, persist rows.

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
from django.db import transaction
from django.utils import timezone
from google.cloud import pubsub_v1
from fantasy.models import Fights

from ufc_data_pipeline.models import FightCreationJob

from .parser import scrape_fights_in_event

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60
_MAX_RETRY_COUNT_BEFORE_FAIL = 3
_IDLE_SHUTDOWN_S = 60
_IDLE_CHECK_INTERVAL_S = 5

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


def parse_message_payload(raw: bytes) -> tuple[str, int]:
    """
    Parse the message payload into a URL and event ID.
    """
    data = json.loads(raw.decode("utf-8"))
    url = str(data["url"]).strip()
    event_id = int(data["event_id"])
    if not url:
        raise ValueError("url is empty")
    return url, event_id


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
    global _LAST_MESSAGE_AT # update the last message at time
    with _STATE_LOCK:
        _LAST_MESSAGE_AT = monotonic() # update the last message at time

    ensure_django()

    # parse the message payload
    try:
        url, event_id = parse_message_payload(message.data) # parse the message payload
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
        message.ack()
        return

    job = FightCreationJob.objects.filter(pubsub_message_id=message.message_id).first() # get the job by the message id

    # If no job found, create a new one
    if job is None:
        try:
            job = FightCreationJob.objects.create(
                pubsub_message_id=message.message_id,
                ran_at=timezone.now(),
                status=FightCreationJob.Status.RUNNING,
                retry_count=0,
                error_msg="",
                url=url,
                event_id=event_id,
            )
        except Exception:
            logger.exception("Failed to create FightCreationJob row")
            message.nack()
            return

    # If the job is completed or failed, acknowledge the message
    if job.status in (
        FightCreationJob.Status.COMPLETED,
        FightCreationJob.Status.FAILED,
    ):
        message.ack()
        return

    # Try to scrape the fights in the event
    try:
        soup = fetch_soup(job.url) # fetch the soup from the event page
        fights = scrape_fights_in_event(soup, job.event_id) # scrape the fights in the event

        # If there are fights, bulk create them
        with transaction.atomic():
            if fights:
                Fights.objects.bulk_create(fights) # bulk create the fights
            job.status = FightCreationJob.Status.COMPLETED # set the job status to completed
            job.completed_at = timezone.now() # set the completed at to current time
            job.error_msg = "" # set the error message to empty
            job.save(update_fields=["status", "completed_at", "error_msg"]) # save the job

        message.ack() # acknowledge the message

    # If there is an error, set the job status to retrying or failed
    except Exception as exc:
        err_text = str(exc) # get the error text
        logger.exception("Fight creation failed for job id=%s", job.pk)
        job.retry_count += 1
        job.error_msg = err_text # set the error message to the error text
        # If the retry count is greater than or equal to the maximum retry count, set the job status to failed
        if job.retry_count >= _MAX_RETRY_COUNT_BEFORE_FAIL:
            job.status = FightCreationJob.Status.FAILED
            job.save(update_fields=["retry_count", "error_msg", "status"])
            message.ack()
        # If the retry count is less than the maximum retry count, set the job status to retrying, send the message back to the subscriber
        else:
            job.status = FightCreationJob.Status.RETRYING
            job.save(update_fields=["retry_count", "error_msg", "status"])
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

    subscriber = pubsub_v1.SubscriberClient() # create a subscriber client
    subscription_path = subscriber.subscription_path(project_id, subscription_id) # create a subscription path
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback) # subscribe to the subscription
    logger.info("Listening on %s", subscription_path)

    with subscriber:
        while True:
            try:
                streaming_pull_future.result(timeout=_IDLE_CHECK_INTERVAL_S) # wait for a message
                break
            except TimeoutError:
                with _STATE_LOCK: # check if the subscriber is idle
                    idle_for_s = monotonic() - _LAST_MESSAGE_AT # calculate the idle time
                # if the idle time is greater than the idle shutdown time, shut down the subscriber
                if idle_for_s > _IDLE_SHUTDOWN_S:
                    logger.info("No messages for %.1fs; shutting down subscriber.", idle_for_s)
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
