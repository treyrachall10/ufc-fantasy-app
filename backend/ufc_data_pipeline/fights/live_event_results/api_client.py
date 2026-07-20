"""
HTTP client for Live Event Results Watcher API reads and lease operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import requests

from ufc_data_pipeline.fights.live_event_results.config import (
    PIPELINE_API_BASE_URL,
    PIPELINE_SERVICE_API_KEY,
)

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60


class ApiClientError(RuntimeError):
    """HTTP API failure with optional status code for retry classification."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def is_conflict(self) -> bool:
        return self.status_code == 409

    @property
    def is_client_error(self) -> bool:
        return self.status_code is not None and 400 <= self.status_code < 500


def _pipeline_headers() -> dict[str, str]:
    if not PIPELINE_API_BASE_URL:
        raise RuntimeError("PIPELINE_API_BASE_URL is not configured")
    if not PIPELINE_SERVICE_API_KEY:
        raise RuntimeError("PIPELINE_SERVICE_API_KEY is not configured")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {PIPELINE_SERVICE_API_KEY}",
    }


def _base_url() -> str:
    return PIPELINE_API_BASE_URL.rstrip("/")


def get_discovery_source() -> dict:
    """GET DiscoverySource for newest-event selection."""
    url = f"{_base_url()}/api/events/DiscoverySource"
    try:
        response = requests.get(
            url,
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"API GET failed status={response.status_code} body={response.text}"
        )
    if not response.content:
        raise RuntimeError("DiscoverySource returned empty body")
    return response.json()


def get_live_results_source(event_id: int) -> dict:
    """GET LiveResultsSource for one event's fights and watcher state."""
    url = f"{_base_url()}/api/events/{event_id}/LiveResultsSource"
    try:
        response = requests.get(
            url,
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if response.status_code == 404:
        raise RuntimeError(f"LiveResultsSource event not found event_id={event_id}")
    if not response.ok:
        raise RuntimeError(
            f"API GET failed status={response.status_code} body={response.text}"
        )
    if not response.content:
        raise RuntimeError("LiveResultsSource returned empty body")
    return response.json()


def _post_lease(event_id: int, action: str, payload: dict[str, Any]) -> dict:
    url = f"{_base_url()}/api/events/{event_id}/LiveResultsLease/{action}"
    try:
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if response.status_code == 409:
        raise RuntimeError(
            f"Lease {action} conflict status=409 body={response.text}"
        )
    if not response.ok:
        raise RuntimeError(
            f"API POST failed status={response.status_code} body={response.text}"
        )
    if not response.content:
        raise RuntimeError(f"LiveResultsLease/{action} returned empty body")
    return response.json()


def claim_lease(event_id: int, owner_token: UUID | str) -> dict:
    """Claim or reclaim the event lease; may return outcome skipped."""
    return _post_lease(event_id, "Claim", {"owner_token": str(owner_token)})


def renew_lease(event_id: int, owner_token: UUID | str) -> dict:
    """Renew an active lease for the current owner."""
    return _post_lease(event_id, "Renew", {"owner_token": str(owner_token)})


def complete_lease(
    event_id: int,
    owner_token: UUID | str,
    *,
    warnings: str = "",
) -> dict:
    """Release the lease after a successful run."""
    return _post_lease(
        event_id,
        "Complete",
        {"owner_token": str(owner_token), "warnings": warnings},
    )


def fail_lease(
    event_id: int,
    owner_token: UUID | str,
    *,
    last_error: str = "",
) -> dict:
    """Release the lease after a failed run."""
    return _post_lease(
        event_id,
        "Fail",
        {"owner_token": str(owner_token), "last_error": last_error},
    )


def _post_fight_action(fight_id: int, action: str, payload: dict[str, Any] | None = None) -> dict:
    url = f"{_base_url()}/api/fights/{fight_id}/{action}"
    try:
        response = requests.post(
            url,
            data=json.dumps(payload or {}),
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise ApiClientError(
            f"API POST {action} failed status={response.status_code} "
            f"body={response.text}",
            status_code=response.status_code,
        )
    if not response.content:
        raise RuntimeError(f"{action} returned empty body")
    return response.json()


def complete_live_fight_transition(fight_id: int, payload: dict[str, Any]) -> dict:
    """Atomically complete a fight and ensure a pending Fight Stats handoff."""
    return _post_fight_action(fight_id, "CompleteLiveFightTransition", payload)


def cancel_live_fight_transition(fight_id: int, payload: dict[str, Any]) -> dict:
    """Atomically cancel an UPCOMING fight; creates no Fight Stats handoff."""
    return _post_fight_action(fight_id, "CancelLiveFightTransition", payload)


def restore_live_fight_upcoming(fight_id: int, payload: dict[str, Any]) -> dict:
    """Atomically restore a CANCELLED fight to UPCOMING."""
    return _post_fight_action(fight_id, "RestoreLiveFightUpcoming", payload)


def mark_fight_stats_handoff_published(fight_id: int) -> dict:
    """Mark Fight Stats handoff published after confirmed Pub/Sub delivery."""
    return _post_fight_action(fight_id, "MarkFightStatsHandoffPublished", {})


def record_fight_stats_handoff_attempt(fight_id: int, *, last_error: str = "") -> dict:
    """Record a failed Fight Stats publication attempt; leave handoff pending."""
    return _post_fight_action(
        fight_id,
        "RecordFightStatsHandoffAttempt",
        {"last_error": last_error},
    )


def _post_event_action(
    event_id: int,
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict:
    url = f"{_base_url()}/api/events/{event_id}/{action}"
    try:
        response = requests.post(
            url,
            data=json.dumps(payload or {}),
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise ApiClientError(
            f"API POST {action} failed status={response.status_code} "
            f"body={response.text}",
            status_code=response.status_code,
        )
    if not response.content:
        raise RuntimeError(f"{action} returned empty body")
    return response.json()


def ensure_live_event_rescrape_handoff(
    event_id: int,
    *,
    card_fingerprint: str,
    reason: str,
) -> dict:
    """Create or reuse a durable rescrape handoff for one card fingerprint."""
    return _post_event_action(
        event_id,
        "EnsureLiveEventRescrapeHandoff",
        {"card_fingerprint": card_fingerprint, "reason": reason},
    )


def mark_live_event_rescrape_published(event_id: int, handoff_id: int) -> dict:
    """Mark a rescrape handoff published after confirmed Pub/Sub delivery."""
    return _post_event_action(
        event_id,
        f"LiveEventRescrapeHandoffs/{handoff_id}/MarkPublished",
        {},
    )


def record_live_event_rescrape_attempt(
    event_id: int,
    handoff_id: int,
    *,
    last_error: str = "",
) -> dict:
    """Record a failed rescrape publication attempt; leave handoff pending."""
    return _post_event_action(
        event_id,
        f"LiveEventRescrapeHandoffs/{handoff_id}/RecordAttempt",
        {"last_error": last_error},
    )


def resolve_live_event_rescrape_handoff(event_id: int, handoff_id: int) -> dict:
    """Mark a rescrape handoff resolved after the card converges."""
    return _post_event_action(
        event_id,
        f"LiveEventRescrapeHandoffs/{handoff_id}/Resolve",
        {},
    )


def fail_live_event_rescrape_handoff(
    event_id: int,
    handoff_id: int,
    *,
    last_error: str = "",
) -> dict:
    """Mark a rescrape handoff failed after exhausted publications."""
    return _post_event_action(
        event_id,
        f"LiveEventRescrapeHandoffs/{handoff_id}/Fail",
        {"last_error": last_error},
    )
