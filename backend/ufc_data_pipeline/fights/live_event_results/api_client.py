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
from ufc_data_pipeline.fights.live_event_results.retry import (
    LeaseOwnerLostError,
    PermanentError,
    TransportError,
    is_retryable_status,
    parse_retry_after,
)

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60


class ApiClientError(RuntimeError):
    """HTTP API failure with status/retry metadata for classification."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds

    @property
    def is_conflict(self) -> bool:
        return self.status_code == 409

    @property
    def is_auth_error(self) -> bool:
        return self.status_code in (401, 403)

    @property
    def is_client_error(self) -> bool:
        """True for non-retryable HTTP 4xx (excludes 408/429)."""
        if self.status_code is None:
            return False
        if is_retryable_status(self.status_code):
            return False
        return 400 <= self.status_code < 500

    @property
    def is_retryable(self) -> bool:
        if self.status_code is None:
            return False
        return is_retryable_status(self.status_code)


def _pipeline_headers() -> dict[str, str]:
    if not PIPELINE_API_BASE_URL:
        raise PermanentError("PIPELINE_API_BASE_URL is not configured")
    if not PIPELINE_SERVICE_API_KEY:
        raise PermanentError("PIPELINE_SERVICE_API_KEY is not configured")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {PIPELINE_SERVICE_API_KEY}",
    }


def _base_url() -> str:
    return PIPELINE_API_BASE_URL.rstrip("/")


def _raise_for_response(response: requests.Response, *, action: str) -> None:
    if response.ok:
        return
    retry_after = parse_retry_after(response.headers.get("Retry-After"))
    message = (
        f"API {action} failed status={response.status_code} body={response.text}"
    )
    if response.status_code in (401, 403):
        raise PermanentError(message)
    if response.status_code == 409:
        raise LeaseOwnerLostError(message)
    raise ApiClientError(
        message,
        status_code=response.status_code,
        retry_after_seconds=retry_after,
    )


def _request(method: str, url: str, *, data: str | None = None) -> requests.Response:
    try:
        return requests.request(
            method,
            url,
            data=data,
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.Timeout as exc:
        raise TransportError(f"API request timed out: {exc}") from exc
    except requests.ConnectionError as exc:
        raise TransportError(f"API connection failed: {exc}") from exc
    except requests.RequestException as exc:
        raise TransportError(f"API request failed: {exc}") from exc


def get_discovery_source() -> dict:
    """GET DiscoverySource for newest-event selection."""
    url = f"{_base_url()}/api/events/DiscoverySource"
    response = _request("GET", url)
    _raise_for_response(response, action="GET DiscoverySource")
    if not response.content:
        raise PermanentError("DiscoverySource returned empty body")
    return response.json()


def get_live_results_source(event_id: int) -> dict:
    """GET LiveResultsSource for one event's fights and watcher state."""
    url = f"{_base_url()}/api/events/{event_id}/LiveResultsSource"
    response = _request("GET", url)
    if response.status_code == 404:
        raise PermanentError(
            f"LiveResultsSource event not found event_id={event_id}"
        )
    _raise_for_response(response, action="GET LiveResultsSource")
    if not response.content:
        raise PermanentError("LiveResultsSource returned empty body")
    return response.json()


def _post_lease(event_id: int, action: str, payload: dict[str, Any]) -> dict:
    url = f"{_base_url()}/api/events/{event_id}/LiveResultsLease/{action}"
    response = _request("POST", url, data=json.dumps(payload))
    _raise_for_response(response, action=f"LiveResultsLease/{action}")
    if not response.content:
        raise PermanentError(f"LiveResultsLease/{action} returned empty body")
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


def _post_fight_action(
    fight_id: int,
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict:
    url = f"{_base_url()}/api/fights/{fight_id}/{action}"
    response = _request("POST", url, data=json.dumps(payload or {}))
    # Fight identity/validation conflicts are permanent, not lease-owner loss.
    if response.status_code == 409:
        raise ApiClientError(
            f"API POST {action} failed status=409 body={response.text}",
            status_code=409,
        )
    _raise_for_response(response, action=action)
    if not response.content:
        raise PermanentError(f"{action} returned empty body")
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
    response = _request("POST", url, data=json.dumps(payload or {}))
    if response.status_code == 409:
        raise ApiClientError(
            f"API POST {action} failed status=409 body={response.text}",
            status_code=409,
        )
    _raise_for_response(response, action=action)
    if not response.content:
        raise PermanentError(f"{action} returned empty body")
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
