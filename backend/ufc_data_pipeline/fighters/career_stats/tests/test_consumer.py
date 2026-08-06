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
    def _make_message(self, payload: dict, *, message_id: str = "msg-1") -> MagicMock:
        message = MagicMock()
        message.data = json.dumps(payload).encode("utf-8")
        message.message_id = message_id
        return message

    def test_invalid_payload_is_acked_without_job_row(self) -> None:
        message = MagicMock()
        message.data = b"not-json"
        message.message_id = "bad"

        consumer.callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()
        assert CareerStatsJob.objects.count() == 0

    def test_non_positive_fight_id_is_acked_without_job_row(self) -> None:
        message = self._make_message({"fight_id": 0})

        consumer.callback(message)

        message.ack.assert_called_once()
        assert CareerStatsJob.objects.count() == 0

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_success_creates_job_marks_completed_and_acks(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        message = self._make_message({"fight_id": 42})

        consumer.callback(message)

        job = CareerStatsJob.objects.get(fight_id=42)
        assert job.status == CareerStatsJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-1"
        assert job.completed_at is not None
        process_mock.assert_called_once_with(42)
        publish_mock.assert_called_once_with(42)
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_success_publishes_score_fight_after_completed_commit(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        message = self._make_message({"fight_id": 99})
        observed: dict[str, object] = {}

        def _capture_publish(fight_id: int) -> str:
            observed["job_status"] = CareerStatsJob.objects.get(
                fight_id=fight_id
            ).status
            observed["process_called"] = process_mock.called
            return "msg-1"

        publish_mock.side_effect = _capture_publish

        consumer.callback(message)

        publish_mock.assert_called_once_with(99)
        assert observed["process_called"] is True
        assert observed["job_status"] == CareerStatsJob.Status.COMPLETED
        assert process_mock.call_count == 1
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_same_message_id_redelivery_after_completed_acks_without_reprocessing(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=10,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.COMPLETED,
            pubsub_message_id="msg-same",
        )
        message = self._make_message({"fight_id": 10}, message_id="msg-same")

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        assert CareerStatsJob.objects.filter(fight_id=10).count() == 1

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_different_message_id_while_running_acks_without_creating(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RUNNING,
            pubsub_message_id="msg-a",
        )
        message = self._make_message({"fight_id": 6}, message_id="msg-b")

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        assert CareerStatsJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_retrying_job_is_resumed_on_redelivery(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        job = CareerStatsJob.objects.create(
            fight_id=5,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary failure",
            pubsub_message_id="msg-retry",
        )
        message = self._make_message({"fight_id": 5}, message_id="msg-retry")

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == CareerStatsJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5)
        publish_mock.assert_called_once_with(5)
        assert CareerStatsJob.objects.filter(fight_id=5).count() == 1
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_completed_job_allows_rescrape_with_new_message_id(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=1,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.COMPLETED,
            pubsub_message_id="msg-old",
        )
        message = self._make_message({"fight_id": 1}, message_id="msg-new")

        consumer.callback(message)

        process_mock.assert_called_once_with(1)
        publish_mock.assert_called_once_with(1)
        message.ack.assert_called_once()
        assert CareerStatsJob.objects.filter(fight_id=1).count() == 2
        assert (
            CareerStatsJob.objects.filter(
                fight_id=1,
                status=CareerStatsJob.Status.COMPLETED,
            ).count()
            == 2
        )

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_failed_job_allows_new_job(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=7,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.FAILED,
            retry_count=3,
            error_msg="gave up",
            pubsub_message_id="msg-failed",
        )
        message = self._make_message({"fight_id": 7}, message_id="msg-after-fail")

        consumer.callback(message)

        process_mock.assert_called_once_with(7)
        publish_mock.assert_called_once_with(7)
        message.ack.assert_called_once()
        assert CareerStatsJob.objects.filter(fight_id=7).count() == 2
        assert CareerStatsJob.objects.filter(
            fight_id=7,
            status=CareerStatsJob.Status.COMPLETED,
        ).exists()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_nacks_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        message = self._make_message({"fight_id": 3})

        consumer.callback(message)

        job = CareerStatsJob.objects.get(fight_id=3)
        assert job.status == CareerStatsJob.Status.RETRYING
        assert job.retry_count == 1
        publish_mock.assert_not_called()
        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acks_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("permanent failure")
        job = CareerStatsJob.objects.create(
            fight_id=4,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RETRYING,
            retry_count=2,
            pubsub_message_id="msg-max",
        )
        message = self._make_message({"fight_id": 4}, message_id="msg-max")

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == CareerStatsJob.Status.FAILED
        assert job.retry_count == 3
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
