"""
Date eligibility helpers for the Live Event Results Watcher.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimezoneConfigError(ValueError):
    """Raised when LIVE_EVENT_RESULTS_TIMEZONE is missing or invalid."""


def require_timezone(name: str) -> ZoneInfo:
    """
    Return a ZoneInfo for ``name`` or raise TimezoneConfigError.
    """
    cleaned = (name or "").strip()
    if not cleaned:
        raise TimezoneConfigError(
            "LIVE_EVENT_RESULTS_TIMEZONE is required and must be a valid IANA name"
        )
    try:
        return ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise TimezoneConfigError(
            f"LIVE_EVENT_RESULTS_TIMEZONE is invalid: {cleaned!r}"
        ) from exc


def local_today(tz: ZoneInfo, *, now: datetime | None = None) -> date:
    """Return the calendar date in ``tz`` for ``now`` (default: UTC now)."""
    current = now if now is not None else datetime.now(tz=ZoneInfo("UTC"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("UTC"))
    return current.astimezone(tz).date()


def is_event_date_eligible(
    event_date: date,
    tz: ZoneInfo,
    *,
    now: datetime | None = None,
) -> bool:
    """
    True when ``event_date`` is local today or yesterday in ``tz``.
    """
    today = local_today(tz, now=now)
    yesterday = today - timedelta(days=1)
    return event_date in (today, yesterday)
