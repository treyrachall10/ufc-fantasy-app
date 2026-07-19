"""
Orchestrate one Live Event Results Watcher pass (lease + card compare).
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
from ufc_data_pipeline.fights.live_event_results.matcher import (
    CardComparisonPlan,
    compare_card,
)
from ufc_data_pipeline.fights.live_event_results.scraper import fetch_event_soup
from ufc_data_pipeline.fights.shared.event_page_fights import parse_event_fight_rows

logger = logging.getLogger(__name__)


class WatchOutcome(str, Enum):
    NO_EVENT = "no_event"
    DATE_INELIGIBLE = "date_ineligible"
    ACTIVE_LEASE_SKIP = "active_lease_skip"
    TERMINAL = "terminal"
    CARD_COMPARED = "card_compared"
    # Outside date window with unresolved handoffs; scrape deferred to later issues.
    PENDING_WITHOUT_SCRAPE = "pending_without_scrape"


@dataclass(frozen=True)
class WatchResult:
    outcome: WatchOutcome
    event_id: int | None = None
    plan: CardComparisonPlan | None = None


_PENDING_HANDOFF_STATES = frozenset({"PENDING", "PUBLISHED"})


def has_unresolved_handoffs(snapshot: dict) -> bool:
    """True when Fight Stats or rescrape handoffs still need watcher attention."""
    for row in snapshot.get("fight_stats_handoffs") or []:
        if (row.get("status") or "").upper() in _PENDING_HANDOFF_STATES:
            return True
    for row in snapshot.get("rescrape_handoffs") or []:
        status = (row.get("status") or "").upper()
        if status in _PENDING_HANDOFF_STATES or status == "FAILED":
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


def _log_comparison_plan(event_id: int, plan: CardComparisonPlan) -> None:
    logger.info(
        "live_event_results card_compared event_id=%s matches=%s "
        "stored_missing=%s source_missing=%s completed_regression_warnings=%s "
        "anomalies=%s",
        event_id,
        len(plan.matches),
        len(plan.stored_missing),
        len(plan.source_missing),
        len(plan.preserve_completed_warnings),
        len(plan.anomalies),
    )
    warning = plan.warning_summary()
    if warning:
        logger.warning(
            "live_event_results card_warnings event_id=%s warnings=%s",
            event_id,
            warning,
        )


def watch_live_event_results() -> WatchResult:
    """
    Run one Live Event Results Watcher pass.

    Selects the newest stored event, applies the timezone date gate, loads the
    fight snapshot, claims the event lease, and for eligible non-terminal events
    fetches the UFC Stats event page once, renews the lease, builds a card
    comparison plan, logs it, and completes without mutating fights or publishing.
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

        if not eligible:
            # Pending handoff drain without new source discovery (later issues).
            api_client.complete_lease(event_id, owner_token)
            logger.info(
                "live_event_results outcome=%s event_id=%s",
                WatchOutcome.PENDING_WITHOUT_SCRAPE.value,
                event_id,
            )
            return WatchResult(
                outcome=WatchOutcome.PENDING_WITHOUT_SCRAPE,
                event_id=event_id,
            )

        event = snapshot.get("event") or {}
        event_url = (event.get("url") or "").strip()
        if not event_url:
            raise RuntimeError(
                f"LiveResultsSource missing event url event_id={event_id}"
            )

        soup = fetch_event_soup(event_url)
        api_client.renew_lease(event_id, owner_token)

        scraped = parse_event_fight_rows(soup)
        plan = compare_card(snapshot.get("fights") or [], scraped)
        _log_comparison_plan(event_id, plan)

        # Issue 034: comparison only — no Fight mutation or Pub/Sub publish.
        api_client.complete_lease(
            event_id,
            owner_token,
            warnings=plan.warning_summary(),
        )
        logger.info(
            "live_event_results outcome=%s event_id=%s",
            WatchOutcome.CARD_COMPARED.value,
            event_id,
        )
        return WatchResult(
            outcome=WatchOutcome.CARD_COMPARED,
            event_id=event_id,
            plan=plan,
        )
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
