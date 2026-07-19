"""
Orchestrate one Live Event Results Watcher pass (lease + transitions + handoffs).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date as Date
from enum import Enum
from uuid import uuid4

from ufc_data_pipeline.fights.live_event_results import api_client
from ufc_data_pipeline.fights.live_event_results.api_client import ApiClientError
from ufc_data_pipeline.fights.live_event_results.config import (
    HANDOFF_BACKOFF_BASE_S,
    HANDOFF_MAX_ATTEMPTS,
    LIVE_EVENT_RESULTS_TIMEZONE,
)
from ufc_data_pipeline.fights.live_event_results.date_gate import (
    TimezoneConfigError,
    is_event_date_eligible,
    require_timezone,
)
from ufc_data_pipeline.fights.live_event_results.matcher import (
    CardComparisonPlan,
    PlanItem,
    compare_card,
)
from ufc_data_pipeline.fights.live_event_results.scraper import fetch_event_soup
from ufc_data_pipeline.fights.shared.event_page_fights import parse_event_fight_rows
from ufc_data_pipeline.shared.publisher import publish_fight_stats_job

logger = logging.getLogger(__name__)


class WatchOutcome(str, Enum):
    NO_EVENT = "no_event"
    DATE_INELIGIBLE = "date_ineligible"
    ACTIVE_LEASE_SKIP = "active_lease_skip"
    TERMINAL = "terminal"
    CARD_COMPARED = "card_compared"
    PENDING_WITHOUT_SCRAPE = "pending_without_scrape"


@dataclass(frozen=True)
class WatchResult:
    outcome: WatchOutcome
    event_id: int | None = None
    plan: CardComparisonPlan | None = None


_PENDING_FIGHT_STATS_STATUS = "PENDING"
_PENDING_RESCRAPE_STATES = frozenset({"PENDING", "PUBLISHED", "FAILED"})


def has_unresolved_handoffs(snapshot: dict) -> bool:
    """True when Fight Stats or rescrape handoffs still need watcher attention."""
    for row in snapshot.get("fight_stats_handoffs") or []:
        if (row.get("status") or "").upper() == _PENDING_FIGHT_STATS_STATUS:
            return True
    for row in snapshot.get("rescrape_handoffs") or []:
        status = (row.get("status") or "").upper()
        if status in _PENDING_RESCRAPE_STATES:
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


def _pending_fight_stats_handoffs(snapshot: dict) -> list[dict]:
    return [
        row
        for row in (snapshot.get("fight_stats_handoffs") or [])
        if (row.get("status") or "").upper() == _PENDING_FIGHT_STATS_STATUS
    ]


def _merge_pending_handoffs(*groups: list[dict]) -> list[dict]:
    by_fight_id: dict[int, dict] = {}
    for group in groups:
        for row in group:
            fight_id = int(row["fight_id"])
            if (row.get("status") or "").upper() != _PENDING_FIGHT_STATS_STATUS:
                continue
            by_fight_id[fight_id] = row
    return [by_fight_id[key] for key in sorted(by_fight_id)]


def _sleep_backoff(attempt: int) -> None:
    delay = HANDOFF_BACKOFF_BASE_S * (2 ** (attempt - 1))
    if delay > 0:
        time.sleep(delay)


def _with_retries(operation_name: str, fn):
    """Run ``fn`` with bounded in-command retries and exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(1, HANDOFF_MAX_ATTEMPTS + 1):
        try:
            return fn()
        except ApiClientError as exc:
            if exc.is_client_error:
                raise
            last_error = exc
        except Exception as exc:
            last_error = exc
        logger.warning(
            "live_event_results %s attempt=%s/%s failed error=%s",
            operation_name,
            attempt,
            HANDOFF_MAX_ATTEMPTS,
            last_error,
        )
        if attempt < HANDOFF_MAX_ATTEMPTS:
            _sleep_backoff(attempt)
    assert last_error is not None
    raise last_error


def _transition_payload(event_id: int, item: PlanItem) -> dict:
    assert item.stored is not None
    assert item.scraped is not None
    scraped = item.scraped
    return {
        "event_id": event_id,
        "fight_url": item.normalized_url or scraped.fight_url,
        "expected_status": "UPCOMING",
        "winner_name": scraped.winner_name,
        "winner_url": scraped.winner_url,
        "method": scraped.method,
        "round": scraped.round,
        "time": scraped.time,
        "round_format": scraped.round_format,
        "weight_class": scraped.weight_class or None,
    }


def apply_completed_transitions(
    event_id: int,
    plan: CardComparisonPlan,
) -> tuple[list[dict], list[str]]:
    """
    For matched UPCOMING→source-completed fights, call the atomic transition API.

    Returns ``(pending_handoffs, failure_messages)``. Continues on per-fight errors.
    """
    pending: list[dict] = []
    failures: list[str] = []

    for item in plan.matches:
        stored = item.stored
        scraped = item.scraped
        if stored is None or scraped is None:
            continue
        if stored.fight_status != "UPCOMING" or not scraped.is_completed:
            continue

        fight_id = stored.fight_id
        payload = _transition_payload(event_id, item)

        def _call_transition(
            fid: int = fight_id,
            body: dict = payload,
        ):
            return api_client.complete_live_fight_transition(fid, body)

        try:
            response = _with_retries(
                f"complete_transition fight_id={fight_id}",
                _call_transition,
            )
        except ApiClientError as exc:
            msg = f"fight_id={fight_id} transition failed: {exc}"
            logger.error("live_event_results %s", msg)
            failures.append(msg)
            continue
        except Exception as exc:
            msg = f"fight_id={fight_id} transition failed: {exc}"
            logger.error("live_event_results %s", msg)
            failures.append(msg)
            continue

        handoff = response.get("handoff") or {}
        status = (handoff.get("status") or "").upper()
        logger.info(
            "live_event_results transition outcome=%s fight_id=%s handoff_status=%s",
            response.get("outcome"),
            fight_id,
            status,
        )
        if status == _PENDING_FIGHT_STATS_STATUS:
            pending.append(handoff)

    return pending, failures


def publish_and_mark_handoff(handoff: dict) -> str | None:
    """
    Publish Fight Stats after a committed handoff, then mark published.

    Returns an error message when the handoff remains pending, else ``None``.
    """
    fight_id = int(handoff["fight_id"])
    fight_url = handoff.get("fight_url") or ""
    last_error: Exception | None = None

    for attempt in range(1, HANDOFF_MAX_ATTEMPTS + 1):
        try:
            publish_fight_stats_job(fight_id, fight_url)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "live_event_results publish failed fight_id=%s attempt=%s/%s error=%s",
                fight_id,
                attempt,
                HANDOFF_MAX_ATTEMPTS,
                exc,
            )
            try:
                api_client.record_fight_stats_handoff_attempt(
                    fight_id,
                    last_error=str(exc),
                )
            except Exception:
                logger.exception(
                    "live_event_results record_attempt_failed fight_id=%s",
                    fight_id,
                )
            if attempt < HANDOFF_MAX_ATTEMPTS:
                _sleep_backoff(attempt)
            continue

        try:
            api_client.mark_fight_stats_handoff_published(fight_id)
            logger.info(
                "live_event_results handoff_published fight_id=%s",
                fight_id,
            )
            return None
        except Exception as exc:
            # Publish succeeded; leave pending so a later run may republish.
            last_error = exc
            logger.warning(
                "live_event_results mark_published_failed fight_id=%s error=%s",
                fight_id,
                exc,
            )
            try:
                api_client.record_fight_stats_handoff_attempt(
                    fight_id,
                    last_error=f"mark_published_failed: {exc}",
                )
            except Exception:
                logger.exception(
                    "live_event_results record_attempt_failed fight_id=%s",
                    fight_id,
                )
            return f"fight_id={fight_id} mark_published failed: {exc}"

    return f"fight_id={fight_id} publish failed: {last_error}"


def drain_pending_handoffs(handoffs: list[dict]) -> list[str]:
    """Publish and mark each pending Fight Stats handoff; return failure messages."""
    failures: list[str] = []
    for handoff in handoffs:
        error = publish_and_mark_handoff(handoff)
        if error:
            failures.append(error)
    return failures


def _raise_if_failures(failures: list[str]) -> None:
    if failures:
        raise RuntimeError(
            "Live Event Results Watcher handoff failures: " + "; ".join(failures)
        )


def watch_live_event_results() -> WatchResult:
    """
    Run one Live Event Results Watcher pass.

    Selects the newest stored event, applies the timezone date gate, loads the
    fight snapshot, claims the event lease, and for eligible non-terminal events
    applies completed transitions and drains durable Fight Stats handoffs.
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
            drain_failures = drain_pending_handoffs(
                _pending_fight_stats_handoffs(snapshot)
            )
            _raise_if_failures(drain_failures)
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

        transition_pending, transition_failures = apply_completed_transitions(
            event_id,
            plan,
        )
        to_drain = _merge_pending_handoffs(
            _pending_fight_stats_handoffs(snapshot),
            transition_pending,
        )
        drain_failures = drain_pending_handoffs(to_drain)
        _raise_if_failures(transition_failures + drain_failures)

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
