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
