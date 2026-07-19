"""
Tests for Live Event Results Watcher service no-work paths.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.service import (
    WatchOutcome,
    apply_cancellations,
    apply_completed_transitions,
    apply_restorations,
    has_unresolved_handoffs,
    has_upcoming_fights,
    is_terminal_snapshot,
    publish_and_mark_handoff,
    watch_live_event_results,
)


def _snapshot(
    *,
    event_id: int = 1,
    fights: list[dict] | None = None,
    fight_stats_handoffs: list[dict] | None = None,
    rescrape_handoffs: list[dict] | None = None,
) -> dict:
    return {
        "event": {
            "event_id": event_id,
            "event": "UFC Live",
            "date": "2026-07-19",
            "url": "http://ufcstats.com/event-details/live",
        },
        "fights": fights or [],
        "watcher_state": None,
        "fight_stats_handoffs": fight_stats_handoffs or [],
        "rescrape_handoffs": rescrape_handoffs or [],
    }


class TerminalHelpersTests(SimpleTestCase):
    def test_upcoming_fight_is_not_terminal(self) -> None:
        snap = _snapshot(
            fights=[{"fight_id": 1, "url": "u", "bout": "a", "fight_status": "UPCOMING"}]
        )
        assert has_upcoming_fights(snap)
        assert not is_terminal_snapshot(snap)

    def test_completed_only_is_terminal(self) -> None:
        snap = _snapshot(
            fights=[
                {
                    "fight_id": 1,
                    "url": "u",
                    "bout": "a",
                    "fight_status": "COMPLETED",
                }
            ]
        )
        assert is_terminal_snapshot(snap)

    def test_pending_fight_stats_handoff_is_not_terminal(self) -> None:
        snap = _snapshot(
            fights=[
                {
                    "fight_id": 1,
                    "url": "u",
                    "bout": "a",
                    "fight_status": "COMPLETED",
                }
            ],
            fight_stats_handoffs=[
                {
                    "fight_id": 1,
                    "event_id": 1,
                    "fight_url": "http://ufcstats.com/fight-details/a",
                    "status": "PENDING",
                }
            ],
        )
        assert has_unresolved_handoffs(snap)
        assert not is_terminal_snapshot(snap)

    def test_published_fight_stats_handoff_is_terminal(self) -> None:
        snap = _snapshot(
            fights=[
                {
                    "fight_id": 1,
                    "url": "u",
                    "bout": "a",
                    "fight_status": "COMPLETED",
                }
            ],
            fight_stats_handoffs=[
                {
                    "fight_id": 1,
                    "event_id": 1,
                    "fight_url": "http://ufcstats.com/fight-details/a",
                    "status": "PUBLISHED",
                }
            ],
        )
        assert not has_unresolved_handoffs(snap)
        assert is_terminal_snapshot(snap)

    def test_cancelled_only_is_terminal(self) -> None:
        snap = _snapshot(
            fights=[
                {
                    "fight_id": 1,
                    "url": "u",
                    "bout": "a",
                    "fight_status": "CANCELLED",
                }
            ]
        )
        assert not has_upcoming_fights(snap)
        assert is_terminal_snapshot(snap)


class WatchLiveEventResultsServiceTests(SimpleTestCase):
    def test_missing_timezone_fails_before_api_calls(self) -> None:
        with patch(
            "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
            "",
        ), patch(
            "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
        ) as discovery:
            with self.assertRaises(Exception):
                watch_live_event_results()
            discovery.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    def test_no_stored_event_exits_successfully(self, discovery) -> None:
        discovery.return_value = {"latest_event": None, "events": []}
        result = watch_live_event_results()
        assert result.outcome == WatchOutcome.NO_EVENT
        assert result.event_id is None

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=False,
    )
    def test_ineligible_event_without_pending_skips_lease(
        self,
        _eligible,
        discovery,
        snapshot,
        claim,
        complete,
    ) -> None:
        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Old",
                "date": "2026-01-01",
                "url": "http://ufcstats.com/event-details/old",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(event_id=7)

        result = watch_live_event_results()

        assert result.outcome == WatchOutcome.DATE_INELIGIBLE
        assert result.event_id == 7
        claim.assert_not_called()
        complete.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=True,
    )
    def test_active_lease_skip(
        self,
        _eligible,
        discovery,
        snapshot,
        claim,
        complete,
    ) -> None:
        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Live",
                "date": "2026-07-19",
                "url": "http://ufcstats.com/event-details/live",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(event_id=7)
        claim.return_value = {
            "outcome": "skipped",
            "skip_reason": "ACTIVE_LEASE",
        }

        result = watch_live_event_results()

        assert result.outcome == WatchOutcome.ACTIVE_LEASE_SKIP
        complete.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=True,
    )
    def test_terminal_event_claims_and_completes_without_scrape(
        self,
        _eligible,
        discovery,
        snapshot,
        claim,
        complete,
    ) -> None:
        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Live",
                "date": "2026-07-19",
                "url": "http://ufcstats.com/event-details/live",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(
            event_id=7,
            fights=[
                {
                    "fight_id": 1,
                    "url": "http://ufcstats.com/fight-details/a",
                    "bout": "A vs. B",
                    "fight_status": "COMPLETED",
                }
            ],
        )
        claim.return_value = {"outcome": "claimed", "status": "RUNNING"}
        complete.return_value = {"outcome": "completed"}

        result = watch_live_event_results()

        assert result.outcome == WatchOutcome.TERMINAL
        assert result.event_id == 7
        claim.assert_called_once()
        complete.assert_called_once()

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.fail_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.renew_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.fetch_event_soup",
        side_effect=RuntimeError("page fetch failed"),
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=True,
    )
    def test_fetch_failure_attempts_fail_release(
        self,
        _eligible,
        discovery,
        snapshot,
        claim,
        _fetch,
        renew,
        complete,
        fail,
    ) -> None:
        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Live",
                "date": "2026-07-19",
                "url": "http://ufcstats.com/event-details/live",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(
            event_id=7,
            fights=[
                {
                    "fight_id": 1,
                    "url": "http://ufcstats.com/fight-details/a",
                    "bout": "A vs. B",
                    "fight_status": "UPCOMING",
                }
            ],
        )
        claim.return_value = {"outcome": "claimed", "status": "RUNNING"}
        fail.return_value = {"outcome": "failed"}

        with self.assertRaises(RuntimeError):
            watch_live_event_results()

        fail.assert_called_once()
        renew.assert_not_called()
        complete.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.renew_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.drain_pending_handoffs",
        return_value=[],
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.apply_completed_transitions",
        return_value=([], []),
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.apply_restorations",
        return_value=[],
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.apply_cancellations"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.parse_event_fight_rows"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.fetch_event_soup"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=True,
    )
    def test_eligible_upcoming_fetches_once_renews_and_compares(
        self,
        _eligible,
        discovery,
        snapshot,
        fetch_soup,
        parse_rows,
        apply_cancel,
        apply_restore,
        apply_transitions,
        drain,
        claim,
        renew,
        complete,
    ) -> None:
        from bs4 import BeautifulSoup

        from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight

        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Live",
                "date": "2026-07-19",
                "url": "http://ufcstats.com/event-details/live",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(
            event_id=7,
            fights=[
                {
                    "fight_id": 1,
                    "url": "http://ufcstats.com/fight-details/a",
                    "bout": "A vs. B",
                    "fight_status": "UPCOMING",
                },
                {
                    "fight_id": 2,
                    "url": "http://ufcstats.com/fight-details/b",
                    "bout": "C vs. D",
                    "fight_status": "UPCOMING",
                },
            ],
        )
        fetch_soup.return_value = BeautifulSoup("<table></table>", "html.parser")
        parse_rows.return_value = [
            ParsedEventFight(
                fight_url="http://ufcstats.com/fight-details/a",
                bout="A vs. B",
                weight_class="LW",
                fighter_a_name="A",
                fighter_a_url="",
                fighter_b_name="B",
                fighter_b_url="",
                is_completed=True,
                winner_name="A",
                method="KO/TKO",
                round=1,
                time=30,
            ),
            ParsedEventFight(
                fight_url="http://ufcstats.com/fight-details/b",
                bout="C vs. D",
                weight_class="WW",
                fighter_a_name="C",
                fighter_a_url="",
                fighter_b_name="D",
                fighter_b_url="",
                is_completed=False,
            ),
        ]
        claim.return_value = {"outcome": "claimed", "status": "RUNNING"}
        renew.return_value = {"outcome": "renewed"}
        complete.return_value = {"outcome": "completed"}

        result = watch_live_event_results()

        assert result.outcome == WatchOutcome.CARD_COMPARED
        assert result.plan is not None
        assert len(result.plan.matches) == 2
        fetch_soup.assert_called_once_with("http://ufcstats.com/event-details/live")
        renew.assert_called_once()
        apply_cancel.assert_called_once()
        apply_restore.assert_called_once()
        apply_transitions.assert_called_once()
        drain.assert_called_once()
        complete.assert_called_once()
        _args, kwargs = complete.call_args
        assert "warnings" in kwargs
        # Renew happens after fetch; complete after compare.
        assert fetch_soup.call_count == 1


class WatchLiveEventResultsCommandTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.management.commands.watch_live_event_results.watch_live_event_results"
    )
    def test_command_exits_successfully_on_no_event(self, watch) -> None:
        from ufc_data_pipeline.fights.live_event_results.service import WatchResult

        watch.return_value = WatchResult(outcome=WatchOutcome.NO_EVENT)
        out = StringIO()
        call_command("watch_live_event_results", stdout=out)
        assert "outcome=no_event" in out.getvalue()

    @patch(
        "ufc_data_pipeline.management.commands.watch_live_event_results.watch_live_event_results"
    )
    def test_command_raises_on_failure(self, watch) -> None:
        watch.side_effect = RuntimeError("api down")
        with self.assertRaises(CommandError):
            call_command("watch_live_event_results")


class WatcherApiOnlyBoundaryTests(SimpleTestCase):
    def test_service_module_does_not_import_domain_or_lease_orm(self) -> None:
        import pathlib

        source = pathlib.Path(
            "ufc_data_pipeline/fights/live_event_results/service.py"
        ).read_text(encoding="utf-8")
        assert "fantasy.models" not in source
        assert "LiveEventResultsState" not in source
        assert "from django.db" not in source
        assert "objects." not in source


class ApplyCompletedTransitionsTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "complete_live_fight_transition"
    )
    def test_transitions_upcoming_completed_matches_only(self, transition) -> None:
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )
        from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight

        plan = CardComparisonPlan(
            matches=[
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        fight_status="UPCOMING",
                    ),
                    scraped=ParsedEventFight(
                        fight_url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        weight_class="LW",
                        fighter_a_name="A",
                        fighter_a_url="",
                        fighter_b_name="B",
                        fighter_b_url="",
                        is_completed=True,
                        winner_name="A",
                        winner_url="http://ufcstats.com/fighter-details/a",
                        method="KO/TKO",
                        round=1,
                        time=30,
                    ),
                    normalized_url="http://ufcstats.com/fight-details/a",
                ),
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=2,
                        url="http://ufcstats.com/fight-details/b",
                        bout="C vs. D",
                        fight_status="UPCOMING",
                    ),
                    scraped=ParsedEventFight(
                        fight_url="http://ufcstats.com/fight-details/b",
                        bout="C vs. D",
                        weight_class="WW",
                        fighter_a_name="C",
                        fighter_a_url="",
                        fighter_b_name="D",
                        fighter_b_url="",
                        is_completed=False,
                    ),
                    normalized_url="http://ufcstats.com/fight-details/b",
                ),
            ]
        )
        transition.return_value = {
            "outcome": "completed",
            "handoff": {
                "fight_id": 1,
                "event_id": 7,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "status": "PENDING",
            },
        }

        pending, failures = apply_completed_transitions(7, plan)

        assert failures == []
        assert len(pending) == 1
        assert pending[0]["fight_id"] == 1
        transition.assert_called_once()
        payload = transition.call_args.args[1]
        assert payload["event_id"] == 7
        assert payload["expected_status"] == "UPCOMING"
        assert payload["winner_name"] == "A"
        assert payload["method"] == "KO/TKO"

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "complete_live_fight_transition"
    )
    def test_completes_cancelled_when_source_has_result(self, transition) -> None:
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )
        from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight

        plan = CardComparisonPlan(
            matches=[
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        fight_status="CANCELLED",
                    ),
                    scraped=ParsedEventFight(
                        fight_url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        weight_class="LW",
                        fighter_a_name="A",
                        fighter_a_url="",
                        fighter_b_name="B",
                        fighter_b_url="",
                        is_completed=True,
                        winner_name="A",
                    ),
                    normalized_url="http://ufcstats.com/fight-details/a",
                )
            ]
        )
        transition.return_value = {
            "outcome": "completed",
            "handoff": {
                "fight_id": 1,
                "event_id": 7,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "status": "PENDING",
            },
        }

        pending, failures = apply_completed_transitions(7, plan)

        assert failures == []
        assert len(pending) == 1
        assert transition.call_args.args[1]["expected_status"] == "CANCELLED"


class ApplyCancellationAndRestoreTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "cancel_live_fight_transition"
    )
    def test_cancels_only_valid_upcoming_missing_from_source(self, cancel) -> None:
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )

        plan = CardComparisonPlan(
            stored_missing=[
                PlanItem(
                    action=MatchAction.STORED_MISSING_FROM_SOURCE,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        fight_status="UPCOMING",
                    ),
                    normalized_url="http://ufcstats.com/fight-details/a",
                ),
                PlanItem(
                    action=MatchAction.STORED_MISSING_FROM_SOURCE,
                    stored=StoredFightRef(
                        fight_id=2,
                        url="http://ufcstats.com/fight-details/b",
                        bout="C vs. D",
                        fight_status="COMPLETED",
                    ),
                    normalized_url="http://ufcstats.com/fight-details/b",
                ),
                PlanItem(
                    action=MatchAction.STORED_MISSING_FROM_SOURCE,
                    stored=StoredFightRef(
                        fight_id=3,
                        url="",
                        bout="E vs. F",
                        fight_status="UPCOMING",
                    ),
                    normalized_url="",
                ),
            ]
        )
        cancel.return_value = {"outcome": "cancelled"}

        apply_cancellations(7, plan)

        cancel.assert_called_once()
        assert cancel.call_args.args[0] == 1
        assert cancel.call_args.args[1]["expected_status"] == "UPCOMING"

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.HANDOFF_MAX_ATTEMPTS",
        1,
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "cancel_live_fight_transition",
        side_effect=RuntimeError("api down"),
    )
    def test_cancel_failure_does_not_raise(self, _cancel) -> None:
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )

        plan = CardComparisonPlan(
            stored_missing=[
                PlanItem(
                    action=MatchAction.STORED_MISSING_FROM_SOURCE,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        fight_status="UPCOMING",
                    ),
                    normalized_url="http://ufcstats.com/fight-details/a",
                )
            ]
        )

        apply_cancellations(7, plan)

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "restore_live_fight_upcoming"
    )
    def test_restores_cancelled_without_source_result(self, restore) -> None:
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )
        from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight

        plan = CardComparisonPlan(
            matches=[
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        fight_status="CANCELLED",
                    ),
                    scraped=ParsedEventFight(
                        fight_url="http://ufcstats.com/fight-details/a",
                        bout="A vs. B",
                        weight_class="LW",
                        fighter_a_name="A",
                        fighter_a_url="",
                        fighter_b_name="B",
                        fighter_b_url="",
                        is_completed=False,
                    ),
                    normalized_url="http://ufcstats.com/fight-details/a",
                )
            ]
        )
        restore.return_value = {"outcome": "restored"}

        failures = apply_restorations(7, plan)

        assert failures == []
        restore.assert_called_once()
        assert restore.call_args.args[1]["expected_status"] == "CANCELLED"

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.HANDOFF_MAX_ATTEMPTS",
        1,
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "complete_live_fight_transition"
    )
    def test_continues_after_per_fight_transition_failure(self, transition) -> None:
        from ufc_data_pipeline.fights.live_event_results.api_client import ApiClientError
        from ufc_data_pipeline.fights.live_event_results.matcher import (
            MatchAction,
            PlanItem,
            StoredFightRef,
            CardComparisonPlan,
        )
        from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight

        def _scraped(fight_id: int, name: str) -> ParsedEventFight:
            return ParsedEventFight(
                fight_url=f"http://ufcstats.com/fight-details/{name}",
                bout=f"{name} vs. X",
                weight_class="LW",
                fighter_a_name=name,
                fighter_a_url="",
                fighter_b_name="X",
                fighter_b_url="",
                is_completed=True,
                winner_name=name,
            )

        plan = CardComparisonPlan(
            matches=[
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=1,
                        url="http://ufcstats.com/fight-details/a",
                        bout="A vs. X",
                        fight_status="UPCOMING",
                    ),
                    scraped=_scraped(1, "a"),
                    normalized_url="http://ufcstats.com/fight-details/a",
                ),
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=StoredFightRef(
                        fight_id=2,
                        url="http://ufcstats.com/fight-details/b",
                        bout="B vs. X",
                        fight_status="UPCOMING",
                    ),
                    scraped=_scraped(2, "b"),
                    normalized_url="http://ufcstats.com/fight-details/b",
                ),
            ]
        )
        transition.side_effect = [
            ApiClientError("ambiguous", status_code=400),
            {
                "outcome": "completed",
                "handoff": {
                    "fight_id": 2,
                    "event_id": 7,
                    "fight_url": "http://ufcstats.com/fight-details/b",
                    "status": "PENDING",
                },
            },
        ]

        pending, failures = apply_completed_transitions(7, plan)

        assert len(failures) == 1
        assert "fight_id=1" in failures[0]
        assert len(pending) == 1
        assert pending[0]["fight_id"] == 2


class PublishAndMarkHandoffTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "mark_fight_stats_handoff_published"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.publish_fight_stats_job"
    )
    def test_publish_then_mark(self, publish, mark) -> None:
        publish.return_value = "msg-1"
        mark.return_value = {"outcome": "published"}

        error = publish_and_mark_handoff(
            {
                "fight_id": 9,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "status": "PENDING",
            }
        )

        assert error is None
        publish.assert_called_once_with(9, "http://ufcstats.com/fight-details/a")
        mark.assert_called_once_with(9)

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service._sleep_backoff"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.HANDOFF_MAX_ATTEMPTS",
        3,
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "record_fight_stats_handoff_attempt"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "mark_fight_stats_handoff_published"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.publish_fight_stats_job",
        side_effect=RuntimeError("pubsub down"),
    )
    def test_publish_failure_records_attempt_and_leaves_pending(
        self,
        publish,
        mark,
        record,
        _sleep,
    ) -> None:
        error = publish_and_mark_handoff(
            {
                "fight_id": 9,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "status": "PENDING",
            }
        )

        assert error is not None
        assert "fight_id=9" in error
        assert publish.call_count == 3
        mark.assert_not_called()
        assert record.call_count == 3

    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "record_fight_stats_handoff_attempt"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client."
        "mark_fight_stats_handoff_published",
        side_effect=RuntimeError("mark failed"),
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.publish_fight_stats_job",
        return_value="msg-1",
    )
    def test_mark_failure_leaves_pending_after_successful_publish(
        self,
        publish,
        mark,
        record,
    ) -> None:
        error = publish_and_mark_handoff(
            {
                "fight_id": 9,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "status": "PENDING",
            }
        )

        assert error is not None
        publish.assert_called_once()
        mark.assert_called_once()
        record.assert_called_once()
        assert "mark_published_failed" in record.call_args.kwargs["last_error"]


class PendingWithoutScrapeDrainTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.LIVE_EVENT_RESULTS_TIMEZONE",
        "America/New_York",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.complete_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.claim_lease"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.drain_pending_handoffs",
        return_value=[],
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.fetch_event_soup"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_live_results_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.api_client.get_discovery_source"
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.service.is_event_date_eligible",
        return_value=False,
    )
    def test_ineligible_with_pending_drains_without_scrape(
        self,
        _eligible,
        discovery,
        snapshot,
        fetch_soup,
        drain,
        claim,
        complete,
    ) -> None:
        discovery.return_value = {
            "latest_event": {
                "event_id": 7,
                "event": "UFC Old",
                "date": "2026-01-01",
                "url": "http://ufcstats.com/event-details/old",
            },
            "events": [],
        }
        snapshot.return_value = _snapshot(
            event_id=7,
            fights=[
                {
                    "fight_id": 1,
                    "url": "http://ufcstats.com/fight-details/a",
                    "bout": "A vs. B",
                    "fight_status": "COMPLETED",
                }
            ],
            fight_stats_handoffs=[
                {
                    "fight_id": 1,
                    "event_id": 7,
                    "fight_url": "http://ufcstats.com/fight-details/a",
                    "status": "PENDING",
                }
            ],
        )
        claim.return_value = {"outcome": "claimed", "status": "RUNNING"}
        complete.return_value = {"outcome": "completed"}

        result = watch_live_event_results()

        assert result.outcome == WatchOutcome.PENDING_WITHOUT_SCRAPE
        fetch_soup.assert_not_called()
        drain.assert_called_once()
        complete.assert_called_once()
