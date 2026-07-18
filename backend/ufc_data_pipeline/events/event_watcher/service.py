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


def select_backfill_events(
    scraped: list[Event],
    cutoff: Date,
) -> list[Event]:
    """
    Return every unique listing event on or after ``cutoff`` (inclusive).

    Backfill replays both known and unknown events, relying on idempotent
    ``SetEvent`` upserts to reuse canonical ``event_id`` values. Receives scraped
    events and an inclusive source-date cutoff; returns deduped events with
    normalized URLs in document order.
    """
    selected: list[Event] = []
    seen_publish_keys: set[tuple[str, str, Date]] = set()

    for row in scraped:
        if row.event_date < cutoff:
            continue
        normalized_url = normalize_event_url(row.url)
        dedupe_key = (normalized_url, row.name, row.event_date)
        if dedupe_key in seen_publish_keys:
            continue
        seen_publish_keys.add(dedupe_key)
        selected.append(
            Event(
                name=row.name,
                url=normalized_url,
                location=row.location,
                event_date=row.event_date,
            )
        )
    return selected


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


def watch_events(
    backfill_from: Date | None = None,
) -> tuple[EventSyncJob, list[Event]]:
    """
    Run one Event Watcher pass and finalize ``EventSyncJob`` status.

    Loads DiscoverySource via API, scrapes the completed-events listing, and then
    selects work depending on mode:

    - Normal mode (``backfill_from is None``): process only events not already
      stored by URL or (name, date).
    - Backfill mode: process every unique listing event on or after the inclusive
      ``backfill_from`` cutoff, replaying both known and unknown events through
      idempotent ``SetEvent`` upserts and the unchanged fights-in-event contract.

    Each selected event is upserted through the API and published to
    fights-in-event after a successful upsert. On success (including no work),
    marks the job COMPLETED.

    Returns
    -------
    tuple[EventSyncJob, list[Event]]
        The job row and the events selected for processing (empty when there is
        no work).
    """
    job = EventSyncJob.objects.create(
        ran_at=timezone.now(),
        status=EventSyncJob.Status.RUNNING,
        retry_count=0,
        error_msg="",
    )

    mode = "backfill" if backfill_from is not None else "normal"

    try:
        discovery = api_client.get_discovery_source()
        soup = fetch_listing_soup()
        scraped = parse_completed_events(soup)
        # determines behavior of the process we are triggering
        if backfill_from is not None:
            selected = select_backfill_events(scraped, backfill_from)
        else:
            selected = find_unknown_events(scraped, discovery)

        if not selected:
            logger.info(
                "Event watcher (%s) found no events to process; nothing to "
                "upsert/publish",
                mode,
            )
        else:
            logger.info(
                "Event watcher (%s) selected %s event(s); upserting and publishing",
                mode,
                len(selected),
            )
            # Track completed handoffs so partial-run failures are auditable.
            # Earlier successes may have upserted/published; retries rely on
            # idempotent SetEvent and replay-safe downstream processing.
            completed = 0
            for event in selected:
                try:
                    _upsert_and_publish(event)
                    completed += 1
                except Exception as exc:
                    raise RuntimeError(
                        "Event watcher failed after completing "
                        f"{completed} of {len(selected)} event(s); "
                        f"failed on url={event.url}: {exc}"
                    ) from exc

        job.status = EventSyncJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.error_msg = ""
        job.save(update_fields=["status", "completed_at", "error_msg"])
        return job, selected
    except Exception as exc:
        job.status = EventSyncJob.Status.FAILED
        job.error_msg = str(exc)
        job.save(update_fields=["status", "error_msg"])
        raise
