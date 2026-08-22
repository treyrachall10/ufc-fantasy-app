"""
Date eligibility helpers for the Live Event Results Watcher.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Local-time reference for docs/operators: UFC cards can run past midnight into
# the early morning. The live window therefore keeps yesterday eligible at and
# after this hour (not only before it).
LIVE_WINDOW_OVERNIGHT_HOUR = 2


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


def _resolve_now(tz: ZoneInfo, now: datetime | None) -> datetime:
    """Return ``now`` in ``tz`` (default: current UTC instant converted to ``tz``)."""
    current = now if now is not None else datetime.now(tz=ZoneInfo("UTC"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("UTC"))
    return current.astimezone(tz)


def local_today(tz: ZoneInfo, *, now: datetime | None = None) -> date:
    """Return the calendar date in ``tz`` for ``now`` (default: UTC now)."""
    return _resolve_now(tz, now).date()


def eligible_live_event_dates(
    tz: ZoneInfo, *, now: datetime | None = None
) -> frozenset[date]:
    """
    Return the set of event dates in the current live-event window.

    In ``tz``, the window is **today** and **yesterday** at every local hour
    (including at or after 02:00). Yesterday stays eligible after midnight so a
    card that runs past midnight remains watchable; future dates are never
    eligible and cannot shadow the active card.
    """
    today = local_today(tz, now=now)
    return frozenset({today, today - timedelta(days=1)})


def is_event_date_eligible(
    event_date: date,
    tz: ZoneInfo,
    *,
    now: datetime | None = None,
) -> bool:
    """
    True when ``event_date`` falls in the live-event window for ``tz``.

    See ``eligible_live_event_dates`` (today or yesterday; future excluded).
    """
    return event_date in eligible_live_event_dates(tz, now=now)


def _event_sort_key(row: Mapping[str, Any]) -> tuple[date, int]:
    raw_date = row.get("date")
    if isinstance(raw_date, date) and not isinstance(raw_date, datetime):
        event_date = raw_date
    elif isinstance(raw_date, str):
        event_date = date.fromisoformat(raw_date)
    else:
        raise ValueError(f"Invalid event date: {raw_date!r}")
    return (event_date, int(row["event_id"]))


def select_live_window_event(
    events: list[Mapping[str, Any]] | None,
    tz: ZoneInfo,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """
    Select one stored event whose date is in the live-event window.

    Does **not** pick the newest event in the database. Filters to
    ``eligible_live_event_dates``, then chooses the maximum by
    ``(date, event_id)`` so ties stay deterministic. Returns ``None`` when no
    stored event falls in the window (future-only rows cannot shadow).
    """
    if not events:
        return None
    eligible = eligible_live_event_dates(tz, now=now)
    candidates: list[Mapping[str, Any]] = []
    for row in events:
        raw_date = row.get("date")
        if isinstance(raw_date, date) and not isinstance(raw_date, datetime):
            event_date = raw_date
        elif isinstance(raw_date, str):
            event_date = date.fromisoformat(raw_date)
        else:
            continue
        if event_date in eligible:
            candidates.append(row)
    if not candidates:
        return None
    best = max(candidates, key=_event_sort_key)
    return dict(best)
