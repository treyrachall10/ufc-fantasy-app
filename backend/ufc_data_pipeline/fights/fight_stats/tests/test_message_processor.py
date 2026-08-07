"""
Tests for fight stats message processor behavior.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.fights.fight_stats import message_processor
from ufc_data_pipeline.models import FightStatsScrapeJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult


class FightStatsMessageProcessorTests(TestCase):
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    def test_success_creates_running_job_marks_completed_and_acknowledges(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/success"

        result = message_processor.process_fight_stats_message(
            "msg-1", 42, fight_url
        )

        job = FightStatsScrapeJob.objects.get(fight_id=42)
        assert result is DeliveryResult.ACKNOWLEDGE
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-1"
        assert job.completed_at is not None
        assert job.fight_url == fight_url
        process_mock.assert_called_once_with(42, fight_url)
        publish_mock.assert_called_once_with(42)

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    def test_success_publishes_career_stats_after_completed_commit(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        fight_url = "http://ufcstats.com/fight-details/publish-after-commit"
        observed: dict[str, object] = {}

        def _capture_publish(fight_id: int) -> str:
            observed["job_status"] = FightStatsScrapeJob.objects.get(
                fight_id=fight_id
            ).status
            observed["process_called"] = process_mock.called
            return "msg-1"

        publish_mock.side_effect = _capture_publish

        result = message_processor.process_fight_stats_message(
            "msg-1", 99, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        publish_mock.assert_called_once_with(99)
        assert observed["process_called"] is True
        assert observed["job_status"] == FightStatsScrapeJob.Status.COMPLETED
        assert process_mock.call_count == 1

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    def test_same_message_id_redelivery_after_completed_acknowledges_without_reprocessing(
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

        result = message_processor.process_fight_stats_message(
            "msg-same", 10, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        assert FightStatsScrapeJob.objects.filter(fight_id=10).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    def test_different_message_id_while_running_acknowledges_without_creating(
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

        result = message_processor.process_fight_stats_message(
            "msg-b", 6, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        assert FightStatsScrapeJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    def test_different_message_id_while_pending_acknowledges_without_creating(
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

        result = message_processor.process_fight_stats_message(
            "msg-other", 8, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        assert FightStatsScrapeJob.objects.filter(fight_id=8).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
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

        result = message_processor.process_fight_stats_message(
            "msg-new", 1, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        process_mock.assert_called_once_with(1, fight_url)
        publish_mock.assert_called_once_with(1)
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

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
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

        result = message_processor.process_fight_stats_message(
            "msg-retry", 5, fight_url
        )

        job.refresh_from_db()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert job.status == FightStatsScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fight_url)
        publish_mock.assert_called_once_with(5)
        assert FightStatsScrapeJob.objects.filter(fight_id=5).count() == 1

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
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

        result = message_processor.process_fight_stats_message(
            "msg-retry-after-fail", 7, fight_url
        )

        assert result is DeliveryResult.ACKNOWLEDGE
        process_mock.assert_called_once_with(7, fight_url)
        publish_mock.assert_called_once_with(7)
        assert FightStatsScrapeJob.objects.filter(fight_id=7).count() == 2
        assert FightStatsScrapeJob.objects.filter(
            fight_id=7,
            status=FightStatsScrapeJob.Status.COMPLETED,
        ).exists()

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_returns_retry_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        fight_url = "http://ufcstats.com/fight-details/retry"

        result = message_processor.process_fight_stats_message(
            "msg-1", 3, fight_url
        )

        job = FightStatsScrapeJob.objects.get(fight_id=3)
        assert result is DeliveryResult.RETRY
        assert job.status == FightStatsScrapeJob.Status.RETRYING
        assert job.retry_count == 1
        publish_mock.assert_not_called()

    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.publish_career_stats_job")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.process_fight_stats")
    @patch("ufc_data_pipeline.fights.fight_stats.message_processor.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acknowledges_without_publish(
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

        result = message_processor.process_fight_stats_message(
            "msg-max", 4, fight_url
        )

        job.refresh_from_db()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert job.status == FightStatsScrapeJob.Status.FAILED
        assert job.retry_count == 3
        publish_mock.assert_not_called()
