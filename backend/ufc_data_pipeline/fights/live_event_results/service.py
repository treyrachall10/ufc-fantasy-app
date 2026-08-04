"""
Orchestrate one Live Event Results Watcher pass (lease + transitions + handoffs).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timezone as datetime_timezone
from enum import Enum
from uuid import uuid4

from ufc_data_pipeline.fights.live_event_results import api_client
from ufc_data_pipeline.fights.live_event_results.api_client import ApiClientError
from ufc_data_pipeline.fights.live_event_results.config import (
    LIVE_EVENT_RESULTS_TIMEZONE,
    RESCRAPE_MAX_PUBLICATIONS,
)
from ufc_data_pipeline.fights.live_event_results.date_gate import (
    TimezoneConfigError,
    is_event_date_eligible,
    require_timezone,
)
from ufc_data_pipeline.fights.live_event_results.fingerprint import (
    build_card_fingerprint,
    card_needs_rescrape,
    rescrape_reason,
)
from ufc_data_pipeline.fights.live_event_results.matcher import (
    CardComparisonPlan,
    PlanItem,
    compare_card,
)
from ufc_data_pipeline.fights.live_event_results.retry import (
    LeaseOwnerLostError,
    PermanentError,
    call_with_retries,
)
from ufc_data_pipeline.fights.live_event_results.scraper import fetch_event_soup
from ufc_data_pipeline.fights.shared.event_page_fights import (
    ParsedEventFight,
    parse_event_fight_rows,
)
from ufc_data_pipeline.shared.fight_stats_publisher import publish_fight_stats_job
from ufc_data_pipeline.shared.fights_in_event_publisher import publish_fights_in_event

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


def _renew_lease(event_id: int, owner_token) -> None:
    """Renew lease ownership; stop the run on owner-token loss."""
    call_with_retries(
        f"renew_lease event_id={event_id}",
        lambda: api_client.renew_lease(event_id, owner_token),
    )


def _complete_lease(event_id: int, owner_token, *, warnings: str = "") -> None:
    call_with_retries(
        f"complete_lease event_id={event_id}",
        lambda: api_client.complete_lease(
            event_id, owner_token, warnings=warnings
        ),
    )


def _fail_lease_best_effort(event_id: int, owner_token, *, last_error: str) -> None:
    try:
        call_with_retries(
            f"fail_lease event_id={event_id}",
            lambda: api_client.fail_lease(
                event_id, owner_token, last_error=last_error
            ),
        )
    except Exception:
        logger.exception(
            "live_event_results lease_fail_release_failed event_id=%s "
            "(recoverable via lease expiration)",
            event_id,
        )


def _transition_payload(event_id: int, item: PlanItem) -> dict:
    assert item.stored is not None
    assert item.scraped is not None
    scraped = item.scraped
    return {
        "event_id": event_id,
        "fight_url": item.normalized_url or scraped.fight_url,
        "expected_status": item.stored.fight_status,
        "winner_name": scraped.winner_name,
        "winner_url": scraped.winner_url,
        "method": scraped.method,
        "round": scraped.round,
        "time": scraped.time,
        "round_format": scraped.round_format,
        "weight_class": scraped.weight_class or None,
    }


def _status_payload(event_id: int, item: PlanItem, *, expected_status: str) -> dict:
    assert item.stored is not None
    return {
        "event_id": event_id,
        "fight_url": item.normalized_url or item.stored.url,
        "expected_status": expected_status,
    }


def apply_cancellations(event_id: int, plan: CardComparisonPlan) -> None:
    """
    Cancel valid stored UPCOMING fights missing from the current source card.

    Cancellation never fails the run; transient failures leave the fight UPCOMING
    for a later schedule.
    """
    for item in plan.stored_missing:
        stored = item.stored
        if stored is None:
            continue
        if not item.normalized_url:
            continue
        if stored.fight_status != "UPCOMING":
            continue

        fight_id = stored.fight_id
        payload = _status_payload(
            event_id,
            item,
            expected_status="UPCOMING",
        )

        def _call_cancel(
            fid: int = fight_id,
            body: dict = payload,
        ):
            return api_client.cancel_live_fight_transition(fid, body)

        try:
            response = call_with_retries(
                f"cancel_transition fight_id={fight_id}",
                _call_cancel,
            )
            logger.info(
                "live_event_results cancel outcome=%s fight_id=%s",
                response.get("outcome"),
                fight_id,
            )
        except LeaseOwnerLostError:
            raise
        except Exception as exc:
            logger.warning(
                "live_event_results cancel_skipped fight_id=%s error=%s",
                fight_id,
                exc,
            )


def apply_restorations(
    event_id: int,
    plan: CardComparisonPlan,
) -> list[str]:
    """
    Restore CANCELLED fights that reappear on the source without a result.

    Returns failure messages for aggregated run failure.
    """
    failures: list[str] = []
    for item in plan.matches:
        stored = item.stored
        scraped = item.scraped
        if stored is None or scraped is None:
            continue
        if stored.fight_status != "CANCELLED" or scraped.is_completed:
            continue

        fight_id = stored.fight_id
        payload = _status_payload(
            event_id,
            item,
            expected_status="CANCELLED",
        )

        def _call_restore(
            fid: int = fight_id,
            body: dict = payload,
        ):
            return api_client.restore_live_fight_upcoming(fid, body)

        try:
            response = call_with_retries(
                f"restore_upcoming fight_id={fight_id}",
                _call_restore,
            )
            logger.info(
                "live_event_results restore outcome=%s fight_id=%s",
                response.get("outcome"),
                fight_id,
            )
        except LeaseOwnerLostError:
            raise
        except (ApiClientError, PermanentError, Exception) as exc:
            msg = f"fight_id={fight_id} restore failed: {exc}"
            logger.error("live_event_results %s", msg)
            failures.append(msg)

    return failures


def apply_completed_transitions(
    event_id: int,
    plan: CardComparisonPlan,
) -> tuple[list[dict], list[str]]:
    """
    For matched UPCOMING/CANCELLED→source-completed fights, call the atomic API.

    Returns ``(pending_handoffs, failure_messages)``. Continues on per-fight errors.
    """
    pending: list[dict] = []
    failures: list[str] = []

    for item in plan.matches:
        stored = item.stored
        scraped = item.scraped
        if stored is None or scraped is None:
            continue
        if stored.fight_status not in ("UPCOMING", "CANCELLED"):
            continue
        if not scraped.is_completed:
            continue

        fight_id = stored.fight_id
        payload = _transition_payload(event_id, item)

        def _call_transition(
            fid: int = fight_id,
            body: dict = payload,
        ):
            return api_client.complete_live_fight_transition(fid, body)

        try:
            response = call_with_retries(
                f"complete_transition fight_id={fight_id}",
                _call_transition,
            )
        except LeaseOwnerLostError:
            raise
        except (ApiClientError, PermanentError, Exception) as exc:
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

    try:
        call_with_retries(
            f"publish_fight_stats fight_id={fight_id}",
            lambda: publish_fight_stats_job(fight_id, fight_url),
        )
    except Exception as exc:
        logger.warning(
            "live_event_results publish failed fight_id=%s error=%s",
            fight_id,
            exc,
        )
        try:
            call_with_retries(
                f"record_fight_stats_attempt fight_id={fight_id}",
                lambda: api_client.record_fight_stats_handoff_attempt(
                    fight_id,
                    last_error=str(exc),
                ),
            )
        except Exception:
            logger.exception(
                "live_event_results record_attempt_failed fight_id=%s",
                fight_id,
            )
        return f"fight_id={fight_id} publish failed: {exc}"

    try:
        call_with_retries(
            f"mark_fight_stats_published fight_id={fight_id}",
            lambda: api_client.mark_fight_stats_handoff_published(fight_id),
        )
        logger.info(
            "live_event_results handoff_published fight_id=%s",
            fight_id,
        )
        return None
    except Exception as exc:
        # Publish succeeded; leave pending so a later run may republish.
        logger.warning(
            "live_event_results mark_published_failed fight_id=%s error=%s",
            fight_id,
            exc,
        )
        try:
            call_with_retries(
                f"record_fight_stats_attempt fight_id={fight_id}",
                lambda: api_client.record_fight_stats_handoff_attempt(
                    fight_id,
                    last_error=f"mark_published_failed: {exc}",
                ),
            )
        except Exception:
            logger.exception(
                "live_event_results record_attempt_failed fight_id=%s",
                fight_id,
            )
        return f"fight_id={fight_id} mark_published failed: {exc}"


def drain_pending_handoffs(handoffs: list[dict]) -> list[str]:
    """Publish and mark each pending Fight Stats handoff; return failure messages."""
    failures: list[str] = []
    for handoff in handoffs:
        error = publish_and_mark_handoff(handoff)
        if error:
            failures.append(error)
    return failures


def _parse_iso_datetime(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return None


def _rescrape_is_due(handoff: dict, *, now: datetime) -> bool:
    status = (handoff.get("status") or "").upper()
    if status == "PENDING":
        return True
    if status != "PUBLISHED":
        return False
    next_eligible = _parse_iso_datetime(handoff.get("next_eligible_at"))
    if next_eligible is None:
        return True
    if next_eligible.tzinfo is None:
        next_eligible = next_eligible.replace(tzinfo=datetime_timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime_timezone.utc)
    return now >= next_eligible


def publish_and_mark_rescrape(
    event_id: int,
    event_url: str,
    handoff: dict,
) -> str | None:
    """
    Publish a Fights In Event rescrape and mark published.

    Returns an error message when publication remains pending, else ``None``.
    """
    handoff_id = int(handoff["id"])
    fingerprint = handoff.get("card_fingerprint") or ""
    reason = handoff.get("reason") or None

    try:
        call_with_retries(
            f"publish_rescrape event_id={event_id} handoff_id={handoff_id}",
            lambda: publish_fights_in_event(
                event_id,
                event_url,
                reason=reason,
                fingerprint=fingerprint,
            ),
        )
    except Exception as exc:
        logger.warning(
            "live_event_results rescrape_publish failed event_id=%s "
            "handoff_id=%s error=%s",
            event_id,
            handoff_id,
            exc,
        )
        try:
            call_with_retries(
                f"record_rescrape_attempt event_id={event_id} handoff_id={handoff_id}",
                lambda: api_client.record_live_event_rescrape_attempt(
                    event_id,
                    handoff_id,
                    last_error=str(exc),
                ),
            )
        except Exception:
            logger.exception(
                "live_event_results rescrape_record_attempt_failed "
                "event_id=%s handoff_id=%s",
                event_id,
                handoff_id,
            )
        return (
            f"event_id={event_id} handoff_id={handoff_id} "
            f"rescrape publish failed: {exc}"
        )

    try:
        call_with_retries(
            f"mark_rescrape_published event_id={event_id} handoff_id={handoff_id}",
            lambda: api_client.mark_live_event_rescrape_published(
                event_id, handoff_id
            ),
        )
        logger.info(
            "live_event_results rescrape_published event_id=%s handoff_id=%s",
            event_id,
            handoff_id,
        )
        return None
    except Exception as exc:
        logger.warning(
            "live_event_results rescrape_mark_published_failed "
            "event_id=%s handoff_id=%s error=%s",
            event_id,
            handoff_id,
            exc,
        )
        try:
            call_with_retries(
                f"record_rescrape_attempt event_id={event_id} handoff_id={handoff_id}",
                lambda: api_client.record_live_event_rescrape_attempt(
                    event_id,
                    handoff_id,
                    last_error=f"mark_published_failed: {exc}",
                ),
            )
        except Exception:
            logger.exception(
                "live_event_results rescrape_record_attempt_failed "
                "event_id=%s handoff_id=%s",
                event_id,
                handoff_id,
            )
        return (
            f"event_id={event_id} handoff_id={handoff_id} "
            f"rescrape mark_published failed: {exc}"
        )


def apply_rescrape_handoffs(
    event_id: int,
    event_url: str,
    plan: CardComparisonPlan,
    scraped: list[ParsedEventFight],
    snapshot: dict,
) -> list[str]:
    """
    Ensure/publish/resolve rescrape handoffs for the current card comparison.

    Publication failures contribute to the aggregate failed exit. Exhausted
    FAILED state is durable operator-action and does not fail the run alone.
    """
    failures: list[str] = []
    now = datetime.now(datetime_timezone.utc)

    if card_needs_rescrape(plan):
        fingerprint = build_card_fingerprint(scraped, plan)
        reason = rescrape_reason(plan)

        def _call_ensure(
            eid: int = event_id,
            fp: str = fingerprint,
            why: str = reason,
        ):
            return api_client.ensure_live_event_rescrape_handoff(
                eid,
                card_fingerprint=fp,
                reason=why,
            )

        try:
            response = call_with_retries(
                f"ensure_rescrape event_id={event_id}",
                _call_ensure,
            )
        except LeaseOwnerLostError:
            raise
        except Exception as exc:
            msg = f"event_id={event_id} ensure_rescrape failed: {exc}"
            logger.error("live_event_results %s", msg)
            failures.append(msg)
            return failures

        handoff = response.get("handoff") or {}
        status = (handoff.get("status") or "").upper()
        publication_count = int(handoff.get("publication_count") or 0)
        handoff_id = int(handoff["id"])

        if status == "FAILED":
            logger.warning(
                "live_event_results rescrape_exhausted event_id=%s "
                "handoff_id=%s fingerprint=%s error=%s",
                event_id,
                handoff_id,
                fingerprint,
                handoff.get("last_error") or "",
            )
            return failures

        if publication_count >= RESCRAPE_MAX_PUBLICATIONS and _rescrape_is_due(
            handoff, now=now
        ):
            try:
                api_client.fail_live_event_rescrape_handoff(
                    event_id,
                    handoff_id,
                    last_error=(
                        "Rescrape publications exhausted after "
                        f"{RESCRAPE_MAX_PUBLICATIONS} cooldown-separated publishes; "
                        "operator action required."
                    ),
                )
            except Exception as exc:
                msg = f"event_id={event_id} fail_rescrape failed: {exc}"
                logger.error("live_event_results %s", msg)
                failures.append(msg)
            return failures

        if _rescrape_is_due(handoff, now=now):
            error = publish_and_mark_rescrape(event_id, event_url, handoff)
            if error:
                failures.append(error)
        else:
            logger.info(
                "live_event_results rescrape_cooldown event_id=%s handoff_id=%s",
                event_id,
                handoff_id,
            )
        return failures

    # Card converged: resolve open rescrape handoffs for this event.
    for row in snapshot.get("rescrape_handoffs") or []:
        status = (row.get("status") or "").upper()
        if status in ("RESOLVED",):
            continue
        handoff_id = int(row["id"])
        try:
            api_client.resolve_live_event_rescrape_handoff(event_id, handoff_id)
            logger.info(
                "live_event_results rescrape_resolved event_id=%s handoff_id=%s",
                event_id,
                handoff_id,
            )
        except Exception as exc:
            msg = f"event_id={event_id} resolve_rescrape handoff_id={handoff_id} failed: {exc}"
            logger.error("live_event_results %s", msg)
            failures.append(msg)
    return failures


def drain_due_rescrape_handoffs(
    event_id: int,
    event_url: str,
    snapshot: dict,
) -> list[str]:
    """Publish due pending/published rescrape handoffs without new card discovery."""
    failures: list[str] = []
    now = datetime.now(datetime_timezone.utc)
    for row in snapshot.get("rescrape_handoffs") or []:
        status = (row.get("status") or "").upper()
        if status in ("RESOLVED", "FAILED"):
            continue
        publication_count = int(row.get("publication_count") or 0)
        if publication_count >= RESCRAPE_MAX_PUBLICATIONS and _rescrape_is_due(
            row, now=now
        ):
            try:
                api_client.fail_live_event_rescrape_handoff(
                    event_id,
                    int(row["id"]),
                    last_error=(
                        "Rescrape publications exhausted after "
                        f"{RESCRAPE_MAX_PUBLICATIONS} cooldown-separated publishes; "
                        "operator action required."
                    ),
                )
            except Exception as exc:
                failures.append(
                    f"event_id={event_id} fail_rescrape handoff_id={row['id']} "
                    f"failed: {exc}"
                )
            continue
        if not _rescrape_is_due(row, now=now):
            continue
        error = publish_and_mark_rescrape(event_id, event_url, row)
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

    discovery = call_with_retries(
        "get_discovery_source",
        api_client.get_discovery_source,
    )
    latest = discovery.get("latest_event")
    if not latest:
        logger.info("live_event_results outcome=%s", WatchOutcome.NO_EVENT.value)
        return WatchResult(outcome=WatchOutcome.NO_EVENT)

    event_id = int(latest["event_id"])
    event_date = _parse_event_date(latest.get("date"))
    snapshot = call_with_retries(
        f"get_live_results_source event_id={event_id}",
        lambda: api_client.get_live_results_source(event_id),
    )
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
    claim = call_with_retries(
        f"claim_lease event_id={event_id}",
        lambda: api_client.claim_lease(event_id, owner_token),
    )
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
            _complete_lease(event_id, owner_token)
            logger.info(
                "live_event_results outcome=%s event_id=%s",
                WatchOutcome.TERMINAL.value,
                event_id,
            )
            return WatchResult(outcome=WatchOutcome.TERMINAL, event_id=event_id)

        if not eligible:
            # Aged pending drain only — no UFC Stats fetch / result discovery.
            event = snapshot.get("event") or {}
            event_url = (event.get("url") or "").strip()
            drain_failures = drain_pending_handoffs(
                _pending_fight_stats_handoffs(snapshot)
            )
            rescrape_failures: list[str] = []
            if event_url:
                rescrape_failures = drain_due_rescrape_handoffs(
                    event_id,
                    event_url,
                    snapshot,
                )
            _raise_if_failures(drain_failures + rescrape_failures)
            _complete_lease(event_id, owner_token)
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
            raise PermanentError(
                f"LiveResultsSource missing event url event_id={event_id}"
            )

        soup = call_with_retries(
            f"fetch_event_soup event_id={event_id}",
            lambda: fetch_event_soup(event_url),
        )
        _renew_lease(event_id, owner_token)

        scraped = parse_event_fight_rows(soup)
        plan = compare_card(snapshot.get("fights") or [], scraped)
        _log_comparison_plan(event_id, plan)

        apply_cancellations(event_id, plan)
        _renew_lease(event_id, owner_token)

        restore_failures = apply_restorations(event_id, plan)
        _renew_lease(event_id, owner_token)

        transition_pending, transition_failures = apply_completed_transitions(
            event_id,
            plan,
        )
        _renew_lease(event_id, owner_token)

        rescrape_failures = apply_rescrape_handoffs(
            event_id,
            event_url,
            plan,
            scraped,
            snapshot,
        )
        _renew_lease(event_id, owner_token)

        to_drain = _merge_pending_handoffs(
            _pending_fight_stats_handoffs(snapshot),
            transition_pending,
        )
        drain_failures = drain_pending_handoffs(to_drain)
        _raise_if_failures(
            restore_failures
            + transition_failures
            + rescrape_failures
            + drain_failures
        )

        _complete_lease(
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
        _fail_lease_best_effort(event_id, owner_token, last_error=str(exc))
        raise
