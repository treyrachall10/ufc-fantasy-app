"""
HTTP client for Event Watcher discovery reads and event upserts via the main API.
"""

from __future__ import annotations

import json
import logging

import requests

from ufc_data_pipeline.events.event_watcher.config import (
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


def get_discovery_source() -> dict:
    """
    GET DiscoverySource for Event Watcher identity comparison.
    Receives no parameters; returns the JSON payload; raises on failure.
    """
    base_url = PIPELINE_API_BASE_URL.rstrip("/")
    url = f"{base_url}/api/events/DiscoverySource"

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


def upsert_event(payload: dict) -> dict:
    """
    PATCH SetEvent to create or update one Events row.
    Receives listing fields; returns JSON with event_id and url; raises on failure.
    """
    base_url = PIPELINE_API_BASE_URL.rstrip("/")
    url = f"{base_url}/api/events/SetEvent"

    try:
        response = requests.patch(
            url,
            data=json.dumps(payload),
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"API PATCH failed status={response.status_code} body={response.text}"
        )

    if not response.content:
        raise RuntimeError("SetEvent returned empty body")
    body = response.json()
    if "event_id" not in body or "url" not in body:
        raise RuntimeError(f"SetEvent response missing event_id/url: {body}")
    return body
