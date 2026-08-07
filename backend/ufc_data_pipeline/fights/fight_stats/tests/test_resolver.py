"""
Tests for fight stats payload validation in the resolver.
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.fight_stats.api.resolver import resolve_fight_stats_message
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


class FightStatsResolverTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fights.fight_stats.api.resolver.process_fight_stats_message",
        return_value=DeliveryResult.ACKNOWLEDGE,
    )
    def test_valid_payload_calls_processor(self, processor_mock: MagicMock) -> None:
        fight_url = "http://ufcstats.com/fight-details/valid"
        payload = {"fight_id": 42, "fight_url": fight_url}

        result = resolve_fight_stats_message("msg-1", payload)

        assert result is DeliveryResult.ACKNOWLEDGE
        processor_mock.assert_called_once_with("msg-1", 42, fight_url)

    def test_missing_fight_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message("msg-1", {"fight_url": "http://example.com"})

    def test_missing_fight_url_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message("msg-1", {"fight_id": 1})

    def test_bool_fight_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message(
                "msg-1",
                {"fight_id": True, "fight_url": "http://ufcstats.com/fight-details/x"},
            )

    def test_non_integer_fight_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message(
                "msg-1",
                {"fight_id": "42", "fight_url": "http://ufcstats.com/fight-details/x"},
            )

    def test_non_positive_fight_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message(
                "msg-1",
                {"fight_id": 0, "fight_url": "http://ufcstats.com/fight-details/x"},
            )

    def test_empty_fight_url_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fight_stats_message("msg-1", {"fight_id": 1, "fight_url": "   "})
