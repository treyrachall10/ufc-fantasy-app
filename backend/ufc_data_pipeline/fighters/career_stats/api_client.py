"""
HTTP client for career-stats source reads and upserts via the main API service.
"""

from __future__ import annotations

import json
import logging

import requests

from ufc_data_pipeline.fighters.career_stats.config import (
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


def _request(method: str, path: str, payload: dict | None = None) -> dict | None:
    base_url = PIPELINE_API_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    try:
        response = requests.request(
            method,
            url,
            data=json.dumps(payload) if payload is not None else None,
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"API {method} failed status={response.status_code} body={response.text}"
        )

    if not response.content:
        return None
    return response.json()


def fetch_career_stats_source(fight_id: int) -> dict:
    """
    GET CareerStatsSource for a fight.
    Receives fight_id; returns the JSON payload; raises on failure.
    """
    payload = _request("GET", f"/api/fights/{fight_id}/CareerStatsSource")
    if payload is None:
        raise RuntimeError(
            f"CareerStatsSource returned empty body for fight_id={fight_id}"
        )
    return payload


def upsert_fighter_career_stats(fighter_id: int, payload: dict) -> None:
    """
    PATCH SetFighterCareerStats for one fighter.
    Receives fighter_id and a full-replace values dict; returns nothing; raises on failure.
    """
    _request(
        "PATCH",
        f"/api/fighters/{fighter_id}/SetFighterCareerStats",
        payload,
    )
