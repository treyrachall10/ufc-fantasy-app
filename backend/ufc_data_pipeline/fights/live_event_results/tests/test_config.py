"""
Tests for Live Event Results configuration wiring.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results import config
from ufc_data_pipeline.fights.live_event_results.date_gate import (
    TimezoneConfigError,
    require_timezone,
)


class LiveEventResultsConfigTests(SimpleTestCase):
    def test_handoff_aliases_track_retry_settings(self) -> None:
        assert config.HANDOFF_MAX_ATTEMPTS == config.RETRY_MAX_ATTEMPTS
        assert config.HANDOFF_BACKOFF_BASE_S == config.RETRY_BACKOFF_BASE_S

    def test_retry_and_lease_settings_are_numeric(self) -> None:
        assert config.RETRY_MAX_ATTEMPTS >= 1
        assert config.RETRY_BACKOFF_BASE_S > 0
        assert config.RETRY_BACKOFF_CAP_S >= config.RETRY_BACKOFF_BASE_S
        assert 0 <= config.RETRY_JITTER_RATIO <= 1
        assert config.RETRY_AFTER_MAX_S > 0
        assert config.LIVE_EVENT_RESULTS_LEASE_SECONDS > 0
        assert config.RESCRAPE_COOLDOWN_SECONDS > 0
        assert config.RESCRAPE_MAX_PUBLICATIONS >= 1

    def test_missing_timezone_rejected(self) -> None:
        with self.assertRaises(TimezoneConfigError):
            require_timezone("")
        with self.assertRaises(TimezoneConfigError):
            require_timezone("Not/A_Real_Zone")
