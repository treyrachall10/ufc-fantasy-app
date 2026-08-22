"""
Tests for Live Event Results date gate and timezone configuration.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.date_gate import (
    LIVE_WINDOW_OVERNIGHT_HOUR,
    TimezoneConfigError,
    eligible_live_event_dates,
    is_event_date_eligible,
    local_today,
    require_timezone,
    select_live_window_event,
)


class RequireTimezoneTests(SimpleTestCase):
    def test_missing_timezone_fails(self) -> None:
        with self.assertRaises(TimezoneConfigError):
            require_timezone("")

    def test_invalid_timezone_fails(self) -> None:
        with self.assertRaises(TimezoneConfigError):
            require_timezone("Not/A_Zone")

    def test_valid_iana_timezone(self) -> None:
        assert require_timezone("America/New_York") == ZoneInfo("America/New_York")


class DateEligibilityTests(SimpleTestCase):
    def test_today_and_yesterday_are_eligible(self) -> None:
        tz = ZoneInfo("America/New_York")
        # 2026-03-09 01:30 UTC == 2026-03-08 20:30 America/New_York (EST).
        now = datetime(2026, 3, 9, 1, 30, tzinfo=ZoneInfo("UTC"))
        today = local_today(tz, now=now)
        assert today == date(2026, 3, 8)
        assert is_event_date_eligible(date(2026, 3, 8), tz, now=now)
        assert is_event_date_eligible(date(2026, 3, 7), tz, now=now)
        assert not is_event_date_eligible(date(2026, 3, 6), tz, now=now)
        assert not is_event_date_eligible(date(2026, 3, 9), tz, now=now)

    def test_yesterday_remains_eligible_before_and_after_overnight_hour(self) -> None:
        """Previous calendar day stays in the window around the 2:00 AM cutoff."""
        tz = ZoneInfo("America/New_York")
        assert LIVE_WINDOW_OVERNIGHT_HOUR == 2

        # 2026-03-08 05:30 UTC == 2026-03-08 00:30 EST (before 2:00 AM).
        before_two = datetime(2026, 3, 8, 5, 30, tzinfo=ZoneInfo("UTC"))
        assert local_today(tz, now=before_two) == date(2026, 3, 8)
        assert eligible_live_event_dates(tz, now=before_two) == frozenset(
            {date(2026, 3, 8), date(2026, 3, 7)}
        )
        assert is_event_date_eligible(date(2026, 3, 7), tz, now=before_two)

        # 2026-03-08 07:30 UTC == 2026-03-08 02:30 EST (at/after 2:00 AM).
        after_two = datetime(2026, 3, 8, 7, 30, tzinfo=ZoneInfo("UTC"))
        assert local_today(tz, now=after_two) == date(2026, 3, 8)
        assert eligible_live_event_dates(tz, now=after_two) == frozenset(
            {date(2026, 3, 8), date(2026, 3, 7)}
        )
        assert is_event_date_eligible(date(2026, 3, 7), tz, now=after_two)

    def test_daylight_saving_spring_forward_boundary(self) -> None:
        tz = ZoneInfo("America/New_York")
        # 2026-03-08 06:30 UTC == 2026-03-08 01:30 EST (before 2am spring forward).
        before = datetime(2026, 3, 8, 6, 30, tzinfo=ZoneInfo("UTC"))
        assert local_today(tz, now=before) == date(2026, 3, 8)

        # 2026-03-08 07:30 UTC == 2026-03-08 03:30 EDT (after spring forward).
        after = datetime(2026, 3, 8, 7, 30, tzinfo=ZoneInfo("UTC"))
        assert local_today(tz, now=after) == date(2026, 3, 8)
        assert is_event_date_eligible(date(2026, 3, 8), tz, now=after)
        assert is_event_date_eligible(date(2026, 3, 7), tz, now=after)


class SelectLiveWindowEventTests(SimpleTestCase):
    def test_returns_none_when_only_future_events_exist(self) -> None:
        tz = ZoneInfo("America/New_York")
        now = datetime(2026, 3, 8, 20, 0, tzinfo=tz)
        selected = select_live_window_event(
            [
                {
                    "event_id": 99,
                    "event": "UFC Future",
                    "date": "2026-03-15",
                    "url": "http://ufcstats.com/event-details/future",
                }
            ],
            tz,
            now=now,
        )
        assert selected is None

    def test_prefers_in_window_event_over_newer_future_event(self) -> None:
        tz = ZoneInfo("America/New_York")
        now = datetime(2026, 3, 8, 20, 0, tzinfo=tz)
        today_event = {
            "event_id": 10,
            "event": "UFC Today",
            "date": "2026-03-08",
            "url": "http://ufcstats.com/event-details/today",
        }
        future_event = {
            "event_id": 20,
            "event": "UFC Future",
            "date": "2026-03-15",
            "url": "http://ufcstats.com/event-details/future",
        }
        selected = select_live_window_event(
            [future_event, today_event],
            tz,
            now=now,
        )
        assert selected is not None
        assert selected["event_id"] == 10

    def test_prefers_newer_date_then_higher_event_id_in_window(self) -> None:
        tz = ZoneInfo("America/New_York")
        # Before 2:00 AM: today and yesterday both eligible.
        now = datetime(2026, 3, 8, 1, 0, tzinfo=tz)
        yesterday_a = {
            "event_id": 1,
            "event": "UFC Yesterday A",
            "date": "2026-03-07",
            "url": "http://ufcstats.com/event-details/y-a",
        }
        yesterday_b = {
            "event_id": 2,
            "event": "UFC Yesterday B",
            "date": "2026-03-07",
            "url": "http://ufcstats.com/event-details/y-b",
        }
        today = {
            "event_id": 3,
            "event": "UFC Today",
            "date": "2026-03-08",
            "url": "http://ufcstats.com/event-details/today",
        }
        selected = select_live_window_event(
            [yesterday_a, yesterday_b, today],
            tz,
            now=now,
        )
        assert selected is not None
        assert selected["event_id"] == 3

        selected_tie = select_live_window_event(
            [yesterday_a, yesterday_b],
            tz,
            now=now,
        )
        assert selected_tie is not None
        assert selected_tie["event_id"] == 2

    def test_selects_yesterday_after_midnight_when_no_today_event(self) -> None:
        tz = ZoneInfo("America/New_York")
        now = datetime(2026, 3, 8, 1, 15, tzinfo=tz)
        selected = select_live_window_event(
            [
                {
                    "event_id": 5,
                    "event": "UFC Saturday",
                    "date": "2026-03-07",
                    "url": "http://ufcstats.com/event-details/sat",
                },
                {
                    "event_id": 50,
                    "event": "UFC Next Week",
                    "date": "2026-03-14",
                    "url": "http://ufcstats.com/event-details/next",
                },
            ],
            tz,
            now=now,
        )
        assert selected is not None
        assert selected["event_id"] == 5
