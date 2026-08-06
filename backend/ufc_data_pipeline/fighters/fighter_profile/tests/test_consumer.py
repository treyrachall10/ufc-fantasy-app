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
    def _make_message(self, payload: dict, *, message_id: str = "msg-1") -> MagicMock:
        message = MagicMock()
        message.data = json.dumps(payload).encode("utf-8")
        message.message_id = message_id
        return message

    def test_invalid_payload_is_acked(self) -> None:
        message = MagicMock()
        message.data = b"not-json"
        message.message_id = "bad"

        consumer.callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_same_message_id_redelivery_after_completed_acks_without_reprocessing(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/redeliver"
        FighterProfileScrapeJob.objects.create(
            fighter_id=10,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.COMPLETED,
            pubsub_message_id="msg-same",
        )
        message = self._make_message(
            {"fighter_id": 10, "fighter_url": fighter_url},
            message_id="msg-same",
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FighterProfileScrapeJob.objects.filter(fighter_id=10).count() == 1

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_different_message_id_while_running_acks_without_creating(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/running"
        FighterProfileScrapeJob.objects.create(
            fighter_id=6,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.RUNNING,
            pubsub_message_id="msg-a",
        )
        message = self._make_message(
            {"fighter_id": 6, "fighter_url": fighter_url},
            message_id="msg-b",
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FighterProfileScrapeJob.objects.filter(fighter_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.fighter_profile.consumer.process_fighter_profile")
    def test_completed_job_allows_rescrape_with_new_message_id(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/completed"
        FighterProfileScrapeJob.objects.create(
            fighter_id=1,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.COMPLETED,
            pubsub_message_id="msg-old",
        )
        message = self._make_message(
            {"fighter_id": 1, "fighter_url": fighter_url},
            message_id="msg-new",
        )

        consumer.callback(message)

        process_mock.assert_called_once_with(1, fighter_url)
        message.ack.assert_called_once()
        assert FighterProfileScrapeJob.objects.filter(fighter_id=1).count() == 2

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
        assert job.pubsub_message_id == "msg-1"
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
            pubsub_message_id="msg-max",
        )
        message = self._make_message(
            {"fighter_id": 4, "fighter_url": fighter_url},
            message_id="msg-max",
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
            pubsub_message_id="msg-retry",
        )
        message = self._make_message(
            {"fighter_id": 5, "fighter_url": fighter_url},
            message_id="msg-retry",
        )

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FighterProfileScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fighter_url)
        assert FighterProfileScrapeJob.objects.filter(fighter_id=5).count() == 1
