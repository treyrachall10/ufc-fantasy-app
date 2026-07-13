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

    @patch("ufc_data_pipeline.fighters.career_stats.consumer.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.consumer.process_career_stats")
    def test_success_creates_job_marks_completed_and_acks(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        message = self._make_message({"fight_id": 42})

        consumer.callback(message)

        job = CareerStatsJob.objects.get(fight_id=42)
        assert job.status == CareerStatsJob.Status.COMPLETED
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
            # Publish must run only after the COMPLETED row is visible outside the save block.
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
    def test_running_job_skips_reprocessing(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RUNNING,
        )
        message = self._make_message({"fight_id": 6})

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
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
        )
        message = self._make_message({"fight_id": 5})

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
    def test_completed_job_is_reprocessed(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=1,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.COMPLETED,
        )
        message = self._make_message({"fight_id": 1})

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
        )
        message = self._make_message({"fight_id": 7})

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
        )
        message = self._make_message({"fight_id": 4})

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == CareerStatsJob.Status.FAILED
        assert job.retry_count == 3
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
