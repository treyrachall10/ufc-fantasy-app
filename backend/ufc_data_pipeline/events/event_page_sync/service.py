"""
Orchestrate fetching the UFC Stats events listing and persisting new ``Events`` rows.
"""

from __future__ import annotations

from datetime import date as Date

import os
import json
import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone

from fantasy.models import Events

from ufc_data_pipeline.events.event_page_sync.config import URL
from ufc_data_pipeline.events.event_page_sync.parser import parse_completed_events_after
from ufc_data_pipeline.models import EventSyncJob

from tenacity import Retrying
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from google.cloud import pubsub_v1


_REQUEST_TIMEOUT_S = 60
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
TOPIC_ID = os.getenv("PUBSUB_FIGHTS_IN_EVENT_TOPIC")

def sync_event_page() -> tuple[EventSyncJob, list[Events]]:
    """
    Record a sync job, ingest newer-than-latest ``Events.date`` rows from UFC Stats,
    and finalize job status.

    Creates an ``event_sync_job`` row with ``ran_at`` and ``status=RUNNING``. Loads the
    latest stored event date (or ``datetime.date.min`` if none), fetches ``config.URL``,
    parses rows, bulk-inserts any ``Events`` not already present for ``(event, date)``,
    then sets ``status=COMPLETED`` and ``completed_at``. On failure, sets ``status`` to
    ``RETRYING``, stores ``error_msg``, and increments ``retry_count``.

    Returns
    -------
    tuple[EventSyncJob, list[Events]]
        The job row and newly created ``Events`` instances (with primary keys set where
        the database supports it for ``bulk_create``).
    """
    publisher = pubsub_v1.PublisherClient() # create a publisher client
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID) # create a topic path

    ran_at = timezone.now()
    job = EventSyncJob.objects.create(
        ran_at=ran_at,
        status=EventSyncJob.Status.RUNNING,
        retry_count=0,
        error_msg="",
    )

    # retry 3 times with exponential backoff
    for attempt in Retrying(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=4, max=15)):
        with attempt:
            try:
                # get latest date or minimum date if no latest date
                latest = (
                    Events.objects.exclude(date__isnull=True).order_by("-date").first()
                )
                cutoff: Date = latest.date if latest else Date.min # get latest date or minimum date if no latest date

                response = requests.get(URL, timeout=_REQUEST_TIMEOUT_S)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser") # parse response content to soup
                parsed = parse_completed_events_after(soup, cutoff) # parse completed events after cutoff

                dates = {row.event_date for row in parsed} # get set of event dates
                existing_pairs: set[tuple[str | None, Date | None]] = set() # create set of existing pairs
                # if dates are not empty, get existing pairs
                if dates:
                    existing_pairs = set(
                        Events.objects.filter(date__in=dates).values_list("event", "date") # get existing pairs
                    )

                # create list of events to create
                to_create = [ 
                    Events(
                        event=row.name,
                        date=row.event_date,
                        location=row.location[:50],
                        url=row.url,
                    )
                    # if event is not in existing pairs, add to list of events to create
                    for row in parsed
                    if (row.name, row.event_date) not in existing_pairs
                ]

                # if there are events to create, bulk create them
                if to_create:
                    with transaction.atomic():
                        objs = Events.objects.bulk_create(to_create) # bulk create events  
                        job.status = EventSyncJob.Status.COMPLETED
                        job.completed_at = timezone.now() # set completed at to current time
                        job.save(update_fields=["status", "completed_at"])

                        # publish messages to Pub/Sub
                        for obj in objs:
                            try:
                                publisher.publish(topic_path, json.dumps({
                                    "url": obj.url,
                                    "event_id": obj.event_id,
                                }).encode("utf-8"))
                            except Exception as exc:
                                raise Exception(f"Failed to publish message to Pub/Sub") from exc

                return job, to_create

            except Exception as exc:
                retry_count = attempt.retry_state.attempt_number # get retry count
                # if retry count is greater than or equal to 3, set status to failed and raise exception
                if retry_count >= 4:
                    job.status = EventSyncJob.Status.FAILED
                    job.error_msg = str(exc)
                    job.save(update_fields=["status", "error_msg"])
                    raise

                # set status to retrying and increment retry count
                job.status = EventSyncJob.Status.RETRYING
                job.error_msg = str(exc)
                job.retry_count += 1
                job.save(update_fields=["status", "error_msg", "retry_count"])
                raise
