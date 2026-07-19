"""
Tests for Live Event Results card comparison.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.matcher import (
    MatchAction,
    compare_card,
)
from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight


def _scraped(
    *,
    url: str,
    completed: bool = False,
    bout: str = "A vs. B",
) -> ParsedEventFight:
    return ParsedEventFight(
        fight_url=url,
        bout=bout,
        weight_class="Lightweight",
        fighter_a_name="A",
        fighter_a_url="http://ufcstats.com/fighter-details/a",
        fighter_b_name="B",
        fighter_b_url="http://ufcstats.com/fighter-details/b",
        is_completed=completed,
        winner_name="A" if completed else None,
        winner_url="http://ufcstats.com/fighter-details/a" if completed else None,
        method="KO/TKO" if completed else None,
        round=1 if completed else None,
        time=60 if completed else None,
    )


class CompareCardTests(SimpleTestCase):
    def test_matches_by_normalized_url(self) -> None:
        stored = [
            {
                "fight_id": 1,
                "url": "http://ufcstats.com/fight-details/abc/",
                "bout": "A vs. B",
                "fight_status": "UPCOMING",
            }
        ]
        scraped = [
            _scraped(url="HTTP://ufcstats.com/fight-details/abc", completed=True)
        ]
        plan = compare_card(stored, scraped)
        assert len(plan.matches) == 1
        assert plan.matches[0].normalized_url == "http://ufcstats.com/fight-details/abc"
        assert plan.matches[0].scraped is not None
        assert plan.matches[0].scraped.is_completed is True

    def test_stored_missing_and_source_missing(self) -> None:
        stored = [
            {
                "fight_id": 1,
                "url": "http://ufcstats.com/fight-details/only-stored",
                "bout": "A vs. B",
                "fight_status": "UPCOMING",
            }
        ]
        scraped = [_scraped(url="http://ufcstats.com/fight-details/only-source")]
        plan = compare_card(stored, scraped)
        assert len(plan.stored_missing) == 1
        assert len(plan.source_missing) == 1
        assert plan.matches == []

    def test_completed_regression_is_preserve_and_warn(self) -> None:
        stored = [
            {
                "fight_id": 1,
                "url": "http://ufcstats.com/fight-details/abc",
                "bout": "A vs. B",
                "fight_status": "COMPLETED",
            }
        ]
        scraped = [_scraped(url="http://ufcstats.com/fight-details/abc", completed=False)]
        plan = compare_card(stored, scraped)
        assert len(plan.preserve_completed_warnings) == 1
        assert (
            plan.preserve_completed_warnings[0].action
            == MatchAction.PRESERVE_COMPLETED_WARN
        )
        # Known match remains available for later processing.
        assert len(plan.matches) == 1

    def test_malformed_and_duplicate_urls_are_anomalies(self) -> None:
        stored = [
            {
                "fight_id": 1,
                "url": "",
                "bout": "bad",
                "fight_status": "UPCOMING",
            },
            {
                "fight_id": 2,
                "url": "http://ufcstats.com/fight-details/dup",
                "bout": "d1",
                "fight_status": "UPCOMING",
            },
            {
                "fight_id": 3,
                "url": "http://ufcstats.com/fight-details/dup",
                "bout": "d2",
                "fight_status": "UPCOMING",
            },
        ]
        scraped = [
            _scraped(url=""),
            _scraped(url="http://ufcstats.com/fight-details/dup", bout="s1"),
            _scraped(url="http://ufcstats.com/fight-details/dup", bout="s2"),
            _scraped(url="http://ufcstats.com/fight-details/ok", bout="ok"),
        ]
        # Add a clean stored match so known fights continue despite anomalies.
        stored.append(
            {
                "fight_id": 4,
                "url": "http://ufcstats.com/fight-details/ok",
                "bout": "ok",
                "fight_status": "UPCOMING",
            }
        )

        plan = compare_card(stored, scraped)
        actions = {item.action for item in plan.anomalies}
        assert MatchAction.MALFORMED_STORED in actions
        assert MatchAction.MALFORMED_SOURCE in actions
        assert MatchAction.DUPLICATE_STORED_URL in actions
        assert MatchAction.DUPLICATE_SOURCE_URL in actions
        assert len(plan.matches) == 1
        assert plan.matches[0].normalized_url == "http://ufcstats.com/fight-details/ok"
