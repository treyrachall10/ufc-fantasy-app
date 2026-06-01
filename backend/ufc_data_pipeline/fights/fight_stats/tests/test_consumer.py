"""
Tests for fight stats Pub/Sub consumer callback behavior.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ufc_data_pipeline.fights.fight_stats import consumer
from ufc_data_pipeline.models import FightStatsScrapeJob


class FightStatsConsumerTests(TestCase):
    def _make_message(self, payload: dict) -> MagicMock:
        message = MagicMock()
        message.data = json.dumps(payload).encode("utf-8")
        return message

    def test_invalid_payload_is_acked_without_job_row(self) -> None:
        message = MagicMock()
        message.data = b"not-json"

        consumer.callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()
        assert FightStatsScrapeJob.objects.count() == 0

    def test_missing_fight_url_is_acked_without_job_row(self) -> None:
        message = self._make_message({"fight_id": 1, "fight_url": "   "})

        consumer.callback(message)

        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.count() == 0

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_success_creates_running_job_marks_completed_and_acks(
        self, process_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/success"
        message = self._make_message({"fight_id": 42, "fight_url": fight_url})

        consumer.callback(message)

        job = FightStatsScrapeJob.objects.get(fight_id=42)
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.completed_at is not None
        assert job.fight_url == fight_url
        process_mock.assert_called_once_with(42, fight_url)
        message.ack.assert_called_once()
        message.nack.assert_not_called()
