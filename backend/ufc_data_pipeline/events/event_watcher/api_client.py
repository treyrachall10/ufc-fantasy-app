"""
HTTP client for Event Watcher discovery reads via the main API service.
"""

from __future__ import annotations

import logging

import requests

from ufc_data_pipeline.events.event_watcher.config import (
    PIPELINE_API_BASE_URL,
    PIPELINE_SERVICE_API_KEY,
)

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60


def get_discovery_source() -> dict:
    """
    GET DiscoverySource for Event Watcher identity comparison.
    Receives no parameters; returns the JSON payload; raises on failure.
    """
    if not PIPELINE_API_BASE_URL:
        raise RuntimeError("PIPELINE_API_BASE_URL is not configured")
    if not PIPELINE_SERVICE_API_KEY:
        raise RuntimeError("PIPELINE_SERVICE_API_KEY is not configured")

    base_url = PIPELINE_API_BASE_URL.rstrip("/")
    url = f"{base_url}/api/events/DiscoverySource"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {PIPELINE_SERVICE_API_KEY}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_S)
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"API GET failed status={response.status_code} body={response.text}"
        )

    if not response.content:
        raise RuntimeError("DiscoverySource returned empty body")
    return response.json()
