"""
Tests for fighter profile Pub/Sub consumer callback behavior.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.fighters.fighter_profile import consumer
from ufc_data_pipeline.models import FighterProfileScrapeJob


class FighterProfileConsumerTests(TestCase):
    def _make_message(self, payload: dict) -> MagicMock:
        message = MagicMock()
        message.data = json.dumps(payload).encode("utf-8")
        return message

    def test_invalid_payload_is_acked(self) -> None:
        message = MagicMock()
        message.data = b"not-json"

        consumer.callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_completed_job_is_reprocessed(self, process_mock: MagicMock) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/completed"
        FighterProfileScrapeJob.objects.create(
            fighter_id=1,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.COMPLETED,
        )
        message = self._make_message(
            {
                "fighter_id": 1,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        process_mock.assert_called_once_with(1, fighter_url)
        message.ack.assert_called_once()
        assert FighterProfileScrapeJob.objects.filter(fighter_id=1).count() == 2

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_running_job_skips_reprocessing(self, process_mock: MagicMock) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/running"
        FighterProfileScrapeJob.objects.create(
            fighter_id=6,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.RUNNING,
        )
        message = self._make_message(
            {
                "fighter_id": 6,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FighterProfileScrapeJob.objects.filter(fighter_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_success_creates_running_job_marks_completed_and_acks(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/success"
        message = self._make_message(
            {
                "fighter_id": 2,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        job = FighterProfileScrapeJob.objects.get(fighter_id=2)
        assert job.status == FighterProfileScrapeJob.Status.COMPLETED
        assert job.completed_at is not None
        assert job.profile_url == fighter_url
        process_mock.assert_called_once_with(2, fighter_url)
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_nacks(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        fighter_url = "http://ufcstats.com/fighter-details/retry"
        message = self._make_message(
            {
                "fighter_id": 3,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        job = FighterProfileScrapeJob.objects.get(fighter_id=3)
        assert job.status == FighterProfileScrapeJob.Status.RETRYING
        assert job.retry_count == 1
        message.nack.assert_called_once()

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acks(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("permanent failure")
        fighter_url = "http://ufcstats.com/fighter-details/failed"
        job = FighterProfileScrapeJob.objects.create(
            fighter_id=4,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.RETRYING,
            retry_count=2,
        )
        message = self._make_message(
            {
                "fighter_id": 4,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FighterProfileScrapeJob.Status.FAILED
        assert job.retry_count == 3
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_retrying_job_is_resumed_on_redelivery(self, process_mock: MagicMock) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/resume"
        job = FighterProfileScrapeJob.objects.create(
            fighter_id=5,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary failure",
        )
        message = self._make_message(
            {
                "fighter_id": 5,
                "fighter_url": fighter_url,
            }
        )

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FighterProfileScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fighter_url)
        assert FighterProfileScrapeJob.objects.filter(fighter_id=5).count() == 1
