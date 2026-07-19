"""
Tests for Live Event Results date gate and timezone configuration.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.date_gate import (
    TimezoneConfigError,
    is_event_date_eligible,
    local_today,
    require_timezone,
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
