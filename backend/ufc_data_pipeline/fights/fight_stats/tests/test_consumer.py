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
        assert FightStatsScrapeJob.objects.count() == 0

    def test_missing_fight_url_is_acked_without_job_row(self) -> None:
        message = self._make_message({"fight_id": 1, "fight_url": "   "})

        consumer.callback(message)

        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.count() == 0

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_success_creates_running_job_marks_completed_and_acks(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/success"
        message = self._make_message({"fight_id": 42, "fight_url": fight_url})

        consumer.callback(message)

        job = FightStatsScrapeJob.objects.get(fight_id=42)
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-1"
        assert job.completed_at is not None
        assert job.fight_url == fight_url
        process_mock.assert_called_once_with(42, fight_url)
        publish_mock.assert_called_once_with(42)
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_success_publishes_career_stats_after_completed_commit(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/publish-after-commit"
        message = self._make_message({"fight_id": 99, "fight_url": fight_url})
        observed: dict[str, object] = {}

        def _capture_publish(fight_id: int) -> str:
            observed["job_status"] = FightStatsScrapeJob.objects.get(
                fight_id=fight_id
            ).status
            observed["process_called"] = process_mock.called
            return "msg-1"

        publish_mock.side_effect = _capture_publish

        consumer.callback(message)

        publish_mock.assert_called_once_with(99)
        assert observed["process_called"] is True
        assert observed["job_status"] == FightStatsScrapeJob.Status.COMPLETED
        assert process_mock.call_count == 1
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_same_message_id_redelivery_after_completed_acks_without_reprocessing(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/redeliver"
        FightStatsScrapeJob.objects.create(
            fight_id=10,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.COMPLETED,
            pubsub_message_id="msg-same",
        )
        message = self._make_message(
            {"fight_id": 10, "fight_url": fight_url},
            message_id="msg-same",
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=10).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_different_message_id_while_running_acks_without_creating(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/running"
        FightStatsScrapeJob.objects.create(
            fight_id=6,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="msg-a",
        )
        message = self._make_message(
            {"fight_id": 6, "fight_url": fight_url},
            message_id="msg-b",
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_different_message_id_while_pending_acks_without_creating(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/pending"
        FightStatsScrapeJob.objects.create(
            fight_id=8,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.PENDING,
            pubsub_message_id="msg-pending",
        )
        message = self._make_message(
            {"fight_id": 8, "fight_url": fight_url},
            message_id="msg-other",
        )

        consumer.callback(message)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=8).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_completed_job_allows_rescrape_with_new_message_id(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/completed"
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.COMPLETED,
            pubsub_message_id="msg-old",
        )
        message = self._make_message(
            {"fight_id": 1, "fight_url": fight_url},
            message_id="msg-new",
        )

        consumer.callback(message)

        process_mock.assert_called_once_with(1, fight_url)
        publish_mock.assert_called_once_with(1)
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 2
        assert (
            FightStatsScrapeJob.objects.filter(
                fight_id=1,
                status=FightStatsScrapeJob.Status.COMPLETED,
            ).count()
            == 2
        )
        assert FightStatsScrapeJob.objects.filter(
            fight_id=1, pubsub_message_id="msg-new"
        ).exists()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_retrying_job_is_resumed_on_redelivery(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/resume"
        job = FightStatsScrapeJob.objects.create(
            fight_id=5,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary failure",
            pubsub_message_id="msg-retry",
        )
        message = self._make_message(
            {"fight_id": 5, "fight_url": fight_url},
            message_id="msg-retry",
        )

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fight_url)
        publish_mock.assert_called_once_with(5)
        assert FightStatsScrapeJob.objects.filter(fight_id=5).count() == 1
        message.ack.assert_called_once()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    def test_failed_job_allows_new_job(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/failed-rescrape"
        FightStatsScrapeJob.objects.create(
            fight_id=7,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.FAILED,
            retry_count=3,
            error_msg="gave up",
            pubsub_message_id="msg-failed",
        )
        message = self._make_message(
            {"fight_id": 7, "fight_url": fight_url},
            message_id="msg-retry-after-fail",
        )

        consumer.callback(message)

        process_mock.assert_called_once_with(7, fight_url)
        publish_mock.assert_called_once_with(7)
        message.ack.assert_called_once()
        assert FightStatsScrapeJob.objects.filter(fight_id=7).count() == 2
        assert FightStatsScrapeJob.objects.filter(
            fight_id=7,
            status=FightStatsScrapeJob.Status.COMPLETED,
        ).exists()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_nacks_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        fight_url = "http://ufcstats.com/fight-details/retry"
        message = self._make_message({"fight_id": 3, "fight_url": fight_url})

        consumer.callback(message)

        job = FightStatsScrapeJob.objects.get(fight_id=3)
        assert job.status == FightStatsScrapeJob.Status.RETRYING
        assert job.retry_count == 1
        publish_mock.assert_not_called()
        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch("ufc_data_pipeline.fights.fight_stats.consumer.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acks_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("permanent failure")
        fight_url = "http://ufcstats.com/fight-details/failed"
        job = FightStatsScrapeJob.objects.create(
            fight_id=4,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RETRYING,
            retry_count=2,
            pubsub_message_id="msg-max",
        )
        message = self._make_message(
            {"fight_id": 4, "fight_url": fight_url},
            message_id="msg-max",
        )

        consumer.callback(message)

        job.refresh_from_db()
        assert job.status == FightStatsScrapeJob.Status.FAILED
        assert job.retry_count == 3
        publish_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
