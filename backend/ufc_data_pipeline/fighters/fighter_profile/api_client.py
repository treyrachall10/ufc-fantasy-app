"""
HTTP client for updating fighter profile metadata via the main API service.
"""

from __future__ import annotations

import json
import logging

import requests

from ufc_data_pipeline.fighters.fighter_profile.config import (
    PIPELINE_API_BASE_URL,
    PIPELINE_SERVICE_API_KEY,
)

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60


def update_fighter_profile(fighter_id: int, payload: dict) -> None:
    """
    PATCH fighter profile metadata through the main API service.
    Receives fighter_id and a payload dict; returns nothing; raises on failure.
    """
    if not PIPELINE_API_BASE_URL:
        raise RuntimeError("PIPELINE_API_BASE_URL is not configured")
    if not PIPELINE_SERVICE_API_KEY:
        raise RuntimeError("PIPELINE_SERVICE_API_KEY is not configured")

    base_url = PIPELINE_API_BASE_URL.rstrip("/")
    url = f"{base_url}/api/fighters/{fighter_id}/SetFighterProfile"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {PIPELINE_SERVICE_API_KEY}",
    }

    # Try to update the fighter profile through the API service.
    try:
        response = requests.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"API update failed status={response.status_code} body={response.text}"
        )
