"""
Tests for fight stats Pub/Sub consumer callback behavior.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.fights.fight_stats import consumer
from ufc_data_pipeline.models import FightStatsScrapeJob


class FightStatsConsumerTests(TestCase):
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

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_running_job_skips_reprocessing(self, process_mock: MagicMock) -> None:
        fight_url = "http://ufcstats.com/fight-details/running"
        FightStatsScrapeJob.objects.create(
            fight_id=6,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
        )
        message = self._make_message({"fight_id": 6, "fight_url": fight_url})

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        assert FightStatsScrapeJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_retrying_job_is_resumed_on_redelivery(self, process_mock: MagicMock) -> None:
        fight_url = "http://ufcstats.com/fight-details/resume"
        job = FightStatsScrapeJob.objects.create(
            fight_id=5,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary failure",
        )
        message = self._make_message({"fight_id": 5, "fight_url": fight_url})

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fight_url)
        assert FightStatsScrapeJob.objects.filter(fight_id=5).count() == 1
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_completed_job_is_reprocessed(self, process_mock: MagicMock) -> None:
        fight_url = "http://ufcstats.com/fight-details/completed"
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.COMPLETED,
        )
        message = self._make_message({"fight_id": 1, "fight_url": fight_url})

        consumer.callback(message)

        process_mock.assert_called_once_with(1, fight_url)
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 2
        assert (
            FightStatsScrapeJob.objects.filter(
                fight_id=1,
                status=FightStatsScrapeJob.Status.COMPLETED,
            ).count()
            == 2
        )

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_failed_job_allows_new_job(self, process_mock: MagicMock) -> None:
        fight_url = "http://ufcstats.com/fight-details/failed-rescrape"
        FightStatsScrapeJob.objects.create(
            fight_id=7,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.FAILED,
            retry_count=3,
            error_msg="gave up",
        )
        message = self._make_message({"fight_id": 7, "fight_url": fight_url})

        consumer.callback(message)

        process_mock.assert_called_once_with(7, fight_url)
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=7).count() == 2
        assert FightStatsScrapeJob.objects.filter(
            fight_id=7,
            status=FightStatsScrapeJob.Status.COMPLETED,
        ).exists()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_nacks(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        fight_url = "http://ufcstats.com/fight-details/retry"
        message = self._make_message({"fight_id": 3, "fight_url": fight_url})

        consumer.callback(message)

        job = FightStatsScrapeJob.objects.get(fight_id=3)
        assert job.status == FightStatsScrapeJob.Status.RETRYING
        assert job.retry_count == 1
        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acks(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("permanent failure")
        fight_url = "http://ufcstats.com/fight-details/failed"
        job = FightStatsScrapeJob.objects.create(
            fight_id=4,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RETRYING,
            retry_count=2,
        )
        message = self._make_message({"fight_id": 4, "fight_url": fight_url})

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FightStatsScrapeJob.Status.FAILED
        assert job.retry_count == 3
        message.ack.assert_called_once()
        message.nack.assert_not_called()
