"""
Tests for deterministic card fingerprints.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.fingerprint import (
    build_card_fingerprint,
    card_needs_rescrape,
    rescrape_reason,
)
from ufc_data_pipeline.fights.live_event_results.matcher import (
    CardComparisonPlan,
    MatchAction,
    PlanItem,
    StoredFightRef,
)
from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight


def _scraped(url: str) -> ParsedEventFight:
    return ParsedEventFight(
        fight_url=url,
        bout="A vs. B",
        weight_class="LW",
        fighter_a_name="A",
        fighter_a_url="",
        fighter_b_name="B",
        fighter_b_url="",
        is_completed=False,
    )


class CardFingerprintTests(SimpleTestCase):
    def test_fingerprint_is_deterministic_and_order_independent(self) -> None:
        scraped = [
            _scraped("http://ufcstats.com/fight-details/b"),
            _scraped("http://ufcstats.com/fight-details/a/"),
        ]
        plan = CardComparisonPlan()
        first = build_card_fingerprint(scraped, plan)
        second = build_card_fingerprint(list(reversed(scraped)), plan)
        assert first == second
        assert len(first) == 64

    def test_malformed_and_duplicate_markers_change_fingerprint(self) -> None:
        scraped = [_scraped("http://ufcstats.com/fight-details/a")]
        clean = build_card_fingerprint(scraped, CardComparisonPlan())
        dirty = build_card_fingerprint(
            scraped,
            CardComparisonPlan(
                anomalies=[
                    PlanItem(
                        action=MatchAction.DUPLICATE_SOURCE_URL,
                        scraped=_scraped("http://ufcstats.com/fight-details/a"),
                        normalized_url="http://ufcstats.com/fight-details/a",
                    ),
                    PlanItem(
                        action=MatchAction.MALFORMED_STORED,
                        stored=StoredFightRef(
                            fight_id=9,
                            url="",
                            bout="x",
                            fight_status="UPCOMING",
                        ),
                    ),
                ]
            ),
        )
        assert clean != dirty

    def test_needs_rescrape_and_reason(self) -> None:
        plan = CardComparisonPlan(
            source_missing=[
                PlanItem(
                    action=MatchAction.SOURCE_MISSING_FROM_STORAGE,
                    scraped=_scraped("http://ufcstats.com/fight-details/new"),
                    normalized_url="http://ufcstats.com/fight-details/new",
                )
            ]
        )
        assert card_needs_rescrape(plan)
        assert rescrape_reason(plan) == "MISSING_FIGHT"

        anomaly_plan = CardComparisonPlan(
            anomalies=[
                PlanItem(
                    action=MatchAction.MALFORMED_SOURCE,
                    scraped=_scraped(""),
                )
            ]
        )
        assert card_needs_rescrape(anomaly_plan)
        assert rescrape_reason(anomaly_plan) == "MALFORMED_IDENTITY"
