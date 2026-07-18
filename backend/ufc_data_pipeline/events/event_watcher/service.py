"""
Orchestrate Event Watcher discovery: API snapshot, listing scrape, upsert, publish.
"""

from __future__ import annotations

import logging
from datetime import date as Date
from urllib.parse import urljoin

from django.utils import timezone

from ufc_data_pipeline.events.event_watcher import api_client
from ufc_data_pipeline.events.event_watcher.config import UFCSTATS_BASE_URL
from ufc_data_pipeline.events.event_watcher.publisher import publish_fights_in_event
from ufc_data_pipeline.events.event_watcher.scraper import fetch_listing_soup
from ufc_data_pipeline.events.shared.parser import Event, parse_completed_events
from ufc_data_pipeline.models import EventSyncJob

logger = logging.getLogger(__name__)


def normalize_event_url(url: str) -> str:
    """
    Normalize a listing or stored event URL to an absolute UFC Stats URL.
    Receives a URL string and returns the absolute form.
    """
    return urljoin(UFCSTATS_BASE_URL + "/", (url or "").strip())


def _stored_identity_sets(discovery: dict) -> tuple[set[str], set[tuple[str, Date]]]:
    urls: set[str] = set()
    pairs: set[tuple[str, Date]] = set()
    for row in discovery.get("events") or []:
        raw_url = row.get("url") or ""
        if raw_url:
            urls.add(normalize_event_url(raw_url))
        name = row.get("event")
        event_date = row.get("date")
        if name and event_date:
            if isinstance(event_date, str):
                event_date = Date.fromisoformat(event_date)
            pairs.add((name, event_date))
    return urls, pairs


def find_unknown_events(
    scraped: list[Event],
    discovery: dict,
) -> list[Event]:
    """
    Return scraped listing events not already stored by URL or (name, date).
    Receives scraped events and a DiscoverySource payload; returns unknown events.
    """
    known_urls, known_pairs = _stored_identity_sets(discovery)
    unknown: list[Event] = []
    seen_publish_keys: set[tuple[str, str, Date]] = set()

    for row in scraped:
        normalized_url = normalize_event_url(row.url)
        if normalized_url in known_urls:
            continue
        if (row.name, row.event_date) in known_pairs:
            continue
        dedupe_key = (normalized_url, row.name, row.event_date)
        if dedupe_key in seen_publish_keys:
            continue
        seen_publish_keys.add(dedupe_key)
        unknown.append(
            Event(
                name=row.name,
                url=normalized_url,
                location=row.location,
                event_date=row.event_date,
            )
        )
    return unknown


def _upsert_and_publish(event: Event) -> dict:
    """
    Persist one unknown listing event via API, then publish fights-in-event.
    Receives a listing Event; returns the SetEvent response body.
    """
    upserted = api_client.upsert_event(
        {
            "event": event.name,
            "date": event.event_date.isoformat(),
            "location": (event.location or "")[:50],
            "url": event.url,
        }
    )
    publish_fights_in_event(int(upserted["event_id"]), str(upserted["url"]))
    return upserted


def watch_events() -> tuple[EventSyncJob, list[Event]]:
    """
    Run one Event Watcher discovery pass and finalize ``EventSyncJob`` status.

    Loads DiscoverySource via API, scrapes the completed-events listing, compares
    identities, upserts each unknown event through the API, and publishes
    fights-in-event after each successful upsert. On success (including no
    unknown events), marks the job COMPLETED.

    Returns
    -------
    tuple[EventSyncJob, list[Event]]
        The job row and unknown scraped events (empty when there is no work).
    """
    job = EventSyncJob.objects.create(
        ran_at=timezone.now(),
        status=EventSyncJob.Status.RUNNING,
        retry_count=0,
        error_msg="",
    )

    try:
        discovery = api_client.get_discovery_source()
        soup = fetch_listing_soup()
        scraped = parse_completed_events(soup)
        unknown = find_unknown_events(scraped, discovery)

        if not unknown:
            logger.info("Event watcher found no new events; nothing to upsert/publish")
        else:
            logger.info(
                "Event watcher discovered %s unknown event(s); upserting and publishing",
                len(unknown),
            )
            # Track completed handoffs so partial-run failures are auditable.
            # Earlier successes may have upserted/published; retries rely on
            # identity comparison + idempotent SetEvent.
            completed = 0
            for event in unknown:
                try:
                    _upsert_and_publish(event)
                    completed += 1
                except Exception as exc:
                    raise RuntimeError(
                        "Event watcher failed after completing "
                        f"{completed} of {len(unknown)} event(s); "
                        f"failed on url={event.url}: {exc}"
                    ) from exc

        job.status = EventSyncJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.error_msg = ""
        job.save(update_fields=["status", "completed_at", "error_msg"])
        return job, unknown
    except Exception as exc:
        job.status = EventSyncJob.Status.FAILED
        job.error_msg = str(exc)
        job.save(update_fields=["status", "error_msg"])
        raise
