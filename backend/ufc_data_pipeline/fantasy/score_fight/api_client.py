"""HTTP client for score-fight source reads and atomic score writes."""

from __future__ import annotations

from typing import Any

import requests

from ufc_data_pipeline.fantasy.score_fight.config import (
    PIPELINE_API_BASE_URL,
    PIPELINE_SERVICE_API_KEY,
)

_REQUEST_TIMEOUT_S = 60


class ScoreFightAPIError(RuntimeError):
    """Base error for score-fight API transport and response failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class ScoringSourceIncompleteError(ScoreFightAPIError):
    """Retryable: upstream scoring inputs are not ready yet."""


class ScoringSourceUnscoreableError(ScoreFightAPIError):
    """Permanent: the fight outcome is intentionally not scoreable."""


def _pipeline_headers() -> dict[str, str]:
    if not PIPELINE_API_BASE_URL:
        raise ScoreFightAPIError("PIPELINE_API_BASE_URL is not configured")
    if not PIPELINE_SERVICE_API_KEY:
        raise ScoreFightAPIError("PIPELINE_SERVICE_API_KEY is not configured")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {PIPELINE_SERVICE_API_KEY}",
    }


def _error_payload(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (ValueError, requests.RequestException):
        return {}
    return payload if isinstance(payload, dict) else {}


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict[str, Any] | None:
    url = f"{PIPELINE_API_BASE_URL.rstrip('/')}{path}"
    try:
        response = requests.request(
            method,
            url,
            json=payload,
            headers=_pipeline_headers(),
            timeout=_REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise ScoreFightAPIError(f"API request failed: {exc}") from exc

    if not response.ok:
        error_payload = _error_payload(response)
        error_code = error_payload.get("error_code")
        detail = error_payload.get("detail") or response.text
        error_type: type[ScoreFightAPIError] = ScoreFightAPIError
        if error_code == "SCORING_SOURCE_INCOMPLETE":
            error_type = ScoringSourceIncompleteError
        elif error_code == "SCORING_SOURCE_UNSCOREABLE":
            error_type = ScoringSourceUnscoreableError
        raise error_type(
            f"API {method} failed status={response.status_code}: {detail}",
            status_code=response.status_code,
            error_code=error_code,
        )

    if not response.content:
        return None
    try:
        response_payload = response.json()
    except ValueError as exc:
        raise ScoreFightAPIError(
            f"API {method} returned invalid JSON",
            status_code=response.status_code,
        ) from exc
    if not isinstance(response_payload, dict):
        raise ScoreFightAPIError(
            f"API {method} returned a non-object JSON response",
            status_code=response.status_code,
        )
    return response_payload


def fetch_scoring_source(fight_id: int) -> dict[str, Any]:
    """Fetch the complete scoreable snapshot for one fight."""
    payload = _request("GET", f"/api/fights/{fight_id}/ScoringSource")
    if payload is None:
        raise ScoreFightAPIError(
            f"ScoringSource returned empty body for fight_id={fight_id}"
        )
    return payload


def set_fight_scoring(fight_id: int, payload: dict) -> None:
    """Atomically persist one fight's complete calculated score state."""
    _request(
        "PATCH",
        f"/api/fights/{fight_id}/SetFightScoring",
        payload,
    )
