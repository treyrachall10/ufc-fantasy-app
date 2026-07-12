"""
Tests for career-stats Pub/Sub consumer callback behavior.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.fighters.career_stats import consumer
from ufc_data_pipeline.models import CareerStatsJob


class CareerStatsConsumerTests(TestCase):
    # Receives a payload dict and returns a mock Pub/Sub message.
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
        assert CareerStatsJob.objects.count() == 0

    def test_non_positive_fight_id_is_acked_without_job_row(self) -> None:
        message = self._make_message({"fight_id": 0})

        consumer.callback(message)

        message.ack.assert_called_once()
        assert CareerStatsJob.objects.count() == 0

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_success_creates_job_marks_completed_and_acks(
        self, process_mock: MagicMock
    ) -> None:
        message = self._make_message({"fight_id": 42})

        consumer.callback(message)

        job = CareerStatsJob.objects.get(fight_id=42)
        assert job.status == CareerStatsJob.Status.COMPLETED
        assert job.completed_at is not None
        process_mock.assert_called_once_with(42)
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_running_job_skips_reprocessing(self, process_mock: MagicMock) -> None:
        CareerStatsJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RUNNING,
        )
        message = self._make_message({"fight_id": 6})

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        assert CareerStatsJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_nacks(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        message = self._make_message({"fight_id": 3})

        consumer.callback(message)

        job = CareerStatsJob.objects.get(fight_id=3)
        assert job.status == CareerStatsJob.Status.RETRYING
        assert job.retry_count == 1
        message.nack.assert_called_once()
        message.ack.assert_not_called()
