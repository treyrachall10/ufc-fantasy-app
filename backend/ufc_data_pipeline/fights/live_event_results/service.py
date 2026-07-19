"""
Orchestrate one Live Event Results Watcher no-work / lease pass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as Date
from enum import Enum
from uuid import uuid4

from ufc_data_pipeline.fights.live_event_results import api_client
from ufc_data_pipeline.fights.live_event_results.config import (
    LIVE_EVENT_RESULTS_TIMEZONE,
)
from ufc_data_pipeline.fights.live_event_results.date_gate import (
    TimezoneConfigError,
    is_event_date_eligible,
    require_timezone,
)

logger = logging.getLogger(__name__)


class WatchOutcome(str, Enum):
    NO_EVENT = "no_event"
    DATE_INELIGIBLE = "date_ineligible"
    ACTIVE_LEASE_SKIP = "active_lease_skip"
    TERMINAL = "terminal"
    # Issue 033 shell: eligible upcoming work exists but scrape is not implemented yet.
    ELIGIBLE_DEFERRED = "eligible_deferred"


@dataclass(frozen=True)
class WatchResult:
    outcome: WatchOutcome
    event_id: int | None = None


_PENDING_HANDOFF_STATES = frozenset({"PENDING", "PUBLISHED"})


def has_unresolved_handoffs(snapshot: dict) -> bool:
    """True when Fight Stats or rescrape handoffs still need watcher attention."""
    for row in snapshot.get("fight_stats_handoffs") or []:
        if (row.get("status") or "").upper() in _PENDING_HANDOFF_STATES:
            return True
    for row in snapshot.get("rescrape_handoffs") or []:
        status = (row.get("status") or "").upper()
        if status in _PENDING_HANDOFF_STATES or status == "FAILED":
            # FAILED rescrape is operator-action state that keeps the event non-terminal.
            return True
    return False


def has_upcoming_fights(snapshot: dict) -> bool:
    """True when any stored fight is still UPCOMING."""
    for fight in snapshot.get("fights") or []:
        if (fight.get("fight_status") or "").upper() == "UPCOMING":
            return True
    return False


def is_terminal_snapshot(snapshot: dict) -> bool:
    """Event is terminal when no upcoming fights and no unresolved handoffs."""
    return not has_upcoming_fights(snapshot) and not has_unresolved_handoffs(snapshot)


def _parse_event_date(raw) -> Date:
    if isinstance(raw, Date):
        return raw
    if isinstance(raw, str):
        return Date.fromisoformat(raw)
    raise ValueError(f"Invalid event date: {raw!r}")


def watch_live_event_results() -> WatchResult:
    """
    Run one Live Event Results Watcher pass without scraping UFC Stats.

    Selects the newest stored event via DiscoverySource, applies the configured
    timezone date gate, loads LiveResultsSource, claims the event lease when
    needed, and exits after terminal/no-work completion. Eligible events that
    still have upcoming fights complete the lease and return ELIGIBLE_DEFERRED
    until a later issue adds page scraping.
    """
    try:
        tz = require_timezone(LIVE_EVENT_RESULTS_TIMEZONE)
    except TimezoneConfigError:
        logger.exception("live_event_results timezone_config_error")
        raise

    discovery = api_client.get_discovery_source()
    latest = discovery.get("latest_event")
    if not latest:
        logger.info("live_event_results outcome=%s", WatchOutcome.NO_EVENT.value)
        return WatchResult(outcome=WatchOutcome.NO_EVENT)

    event_id = int(latest["event_id"])
    event_date = _parse_event_date(latest.get("date"))
    snapshot = api_client.get_live_results_source(event_id)
    pending = has_unresolved_handoffs(snapshot)
    eligible = is_event_date_eligible(event_date, tz)

    if not eligible and not pending:
        logger.info(
            "live_event_results outcome=%s event_id=%s event_date=%s",
            WatchOutcome.DATE_INELIGIBLE.value,
            event_id,
            event_date.isoformat(),
        )
        return WatchResult(outcome=WatchOutcome.DATE_INELIGIBLE, event_id=event_id)

    owner_token = uuid4()
    claim = api_client.claim_lease(event_id, owner_token)
    if claim.get("outcome") == "skipped":
        logger.info(
            "live_event_results outcome=%s event_id=%s owner_token_suffix=%s",
            WatchOutcome.ACTIVE_LEASE_SKIP.value,
            event_id,
            str(owner_token)[-8:],
        )
        return WatchResult(outcome=WatchOutcome.ACTIVE_LEASE_SKIP, event_id=event_id)

    logger.info(
        "live_event_results lease_claimed event_id=%s owner_token_suffix=%s",
        event_id,
        str(owner_token)[-8:],
    )

    try:
        if is_terminal_snapshot(snapshot):
            api_client.complete_lease(event_id, owner_token)
            logger.info(
                "live_event_results outcome=%s event_id=%s",
                WatchOutcome.TERMINAL.value,
                event_id,
            )
            return WatchResult(outcome=WatchOutcome.TERMINAL, event_id=event_id)

        # Issue 033: no UFC Stats scrape yet; release lease cleanly.
        api_client.complete_lease(event_id, owner_token)
        logger.info(
            "live_event_results outcome=%s event_id=%s",
            WatchOutcome.ELIGIBLE_DEFERRED.value,
            event_id,
        )
        return WatchResult(outcome=WatchOutcome.ELIGIBLE_DEFERRED, event_id=event_id)
    except Exception as exc:
        logger.exception(
            "live_event_results outcome=failure event_id=%s error=%s",
            event_id,
            exc,
        )
        try:
            api_client.fail_lease(event_id, owner_token, last_error=str(exc))
        except Exception:
            logger.exception(
                "live_event_results lease_fail_release_failed event_id=%s "
                "(recoverable via lease expiration)",
                event_id,
            )
        raise
