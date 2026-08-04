"""
Bounded retry policy for Live Event Results Watcher external operations.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

import requests

from ufc_data_pipeline.fights.live_event_results.config import (
    RETRY_AFTER_MAX_S,
    RETRY_BACKOFF_BASE_S,
    RETRY_BACKOFF_CAP_S,
    RETRY_JITTER_RATIO,
    RETRY_MAX_ATTEMPTS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PermanentError(RuntimeError):
    """Non-retryable failure (validation, auth, conflict, configuration)."""


class LeaseOwnerLostError(PermanentError):
    """Lease owner-token fencing lost; stop further mutations for this run."""


class TransportError(RuntimeError):
    """Retryable connection, DNS, or timeout failure."""


def parse_retry_after(
    header_value: str | None,
    *,
    max_seconds: float = RETRY_AFTER_MAX_S,
) -> float | None:
    """
    Parse a Retry-After header into seconds, clipped to ``max_seconds``.

    Supports delay-seconds only (not HTTP-date).
    """
    if header_value is None:
        return None
    raw = str(header_value).strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None
    if seconds < 0:
        return None
    return min(seconds, max_seconds)


def is_retryable_status(status_code: int | None) -> bool:
    """HTTP statuses that may be retried under the watcher policy."""
    if status_code is None:
        return False
    if status_code in (408, 429):
        return True
    return status_code >= 500


def is_retryable_exception(exc: BaseException) -> bool:
    """Classify whether ``exc`` should be retried."""
    if isinstance(exc, PermanentError):
        return False
    if isinstance(exc, (ValueError, TypeError, AssertionError, KeyError)):
        return False
    if isinstance(exc, TransportError):
        return True
    if isinstance(exc, requests.Timeout):
        return True
    if isinstance(exc, requests.ConnectionError):
        return True
    if isinstance(exc, TimeoutError):
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return is_retryable_status(status)
    # Default: retry other external failures (Pub/Sub, Playwright, etc.).
    return True


def compute_backoff_seconds(
    attempt: int,
    *,
    base_seconds: float = RETRY_BACKOFF_BASE_S,
    cap_seconds: float = RETRY_BACKOFF_CAP_S,
    jitter_ratio: float = RETRY_JITTER_RATIO,
    retry_after_seconds: float | None = None,
    rng: Callable[[], float] | None = None,
) -> float:
    """
    Exponential backoff with jitter for attempt ``1..N``.

    Nominal delays are around ``base``, ``2*base``, ``4*base``, capped by
    ``cap_seconds``. When ``retry_after_seconds`` is present, use the larger of
    backoff and the bounded Retry-After value.
    """
    if attempt < 1:
        attempt = 1
    delay = min(base_seconds * (2 ** (attempt - 1)), cap_seconds)
    if jitter_ratio > 0:
        rand = rng() if rng is not None else random.random()
        factor = 1.0 + jitter_ratio * (2.0 * rand - 1.0)
        delay = max(0.0, delay * factor)
    if retry_after_seconds is not None:
        bounded_retry_after = min(float(retry_after_seconds), RETRY_AFTER_MAX_S)
        delay = max(delay, bounded_retry_after)
    return delay


def _retry_after_from_exc(exc: BaseException) -> float | None:
    return getattr(exc, "retry_after_seconds", None)


def call_with_retries(
    operation_name: str,
    fn: Callable[[], T],
    *,
    max_attempts: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] | None = None,
) -> T:
    """
    Run ``fn`` with at most ``max_attempts`` total tries and exponential backoff.

    Non-retryable errors raise immediately. Exhausted retryable errors re-raise
    the last exception.
    """
    attempts = RETRY_MAX_ATTEMPTS if max_attempts is None else max_attempts
    if attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if not is_retryable_exception(exc):
                raise
            logger.warning(
                "live_event_results retry operation=%s attempt=%s/%s error=%s",
                operation_name,
                attempt,
                attempts,
                exc,
            )
            if attempt >= attempts:
                break
            delay = compute_backoff_seconds(
                attempt,
                retry_after_seconds=_retry_after_from_exc(exc),
                rng=rng,
            )
            if delay > 0:
                sleep_fn(delay)

    assert last_error is not None
    raise last_error
