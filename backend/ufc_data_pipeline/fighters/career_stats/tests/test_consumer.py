"""
Tests for career-stats message processor and resolver.
"""

from __future__ import annotations

import base64
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from ufc_data_pipeline.fighters.career_stats.api.resolver import (
    resolve_career_stats_message,
)
from ufc_data_pipeline.fighters.career_stats.message_processor import (
    process_career_stats_message,
)
from ufc_data_pipeline.models import CareerStatsJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


class CareerStatsMessageProcessorTests(TestCase):
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    def test_success_creates_job_marks_completed_and_acknowledges(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        result = process_career_stats_message("msg-1", 42)

        job = CareerStatsJob.objects.get(fight_id=42)
        assert job.status == CareerStatsJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-1"
        assert job.completed_at is not None
        process_mock.assert_called_once_with(42)
        publish_mock.assert_called_once_with(42)
        assert result is DeliveryResult.ACKNOWLEDGE

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    def test_success_publishes_score_fight_after_completed_commit(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        observed: dict[str, object] = {}

        def _capture_publish(fight_id: int) -> str:
            observed["job_status"] = CareerStatsJob.objects.get(
                fight_id=fight_id
            ).status
            observed["process_called"] = process_mock.called
            return "msg-1"

        publish_mock.side_effect = _capture_publish

        result = process_career_stats_message("msg-1", 99)

        publish_mock.assert_called_once_with(99)
        assert observed["process_called"] is True
        assert observed["job_status"] == CareerStatsJob.Status.COMPLETED
        assert process_mock.call_count == 1
        assert result is DeliveryResult.ACKNOWLEDGE

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    def test_same_message_id_redelivery_after_completed_acknowledges_without_reprocessing(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=10,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.COMPLETED,
            pubsub_message_id="msg-same",
        )

        result = process_career_stats_message("msg-same", 10)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert CareerStatsJob.objects.filter(fight_id=10).count() == 1

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    def test_different_message_id_while_running_acknowledges_without_creating(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RUNNING,
            pubsub_message_id="msg-a",
            lease_expires_at=timezone.now() + timedelta(minutes=5),
        )

        result = process_career_stats_message("msg-b", 6)

        process_mock.assert_not_called()
        publish_mock.assert_not_called()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert CareerStatsJob.objects.filter(fight_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
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

        result = process_career_stats_message("msg-retry", 5)

        job.refresh_from_db()
        assert job.status == CareerStatsJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5)
        publish_mock.assert_called_once_with(5)
        assert CareerStatsJob.objects.filter(fight_id=5).count() == 1
        assert result is DeliveryResult.ACKNOWLEDGE

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    def test_completed_job_allows_rescrape_with_new_message_id(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        CareerStatsJob.objects.create(
            fight_id=1,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.COMPLETED,
            pubsub_message_id="msg-old",
        )

        result = process_career_stats_message("msg-new", 1)

        process_mock.assert_called_once_with(1)
        publish_mock.assert_called_once_with(1)
        assert result is DeliveryResult.ACKNOWLEDGE
        assert CareerStatsJob.objects.filter(fight_id=1).count() == 2
        assert (
            CareerStatsJob.objects.filter(
                fight_id=1,
                status=CareerStatsJob.Status.COMPLETED,
            ).count()
            == 2
        )

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
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

        result = process_career_stats_message("msg-after-fail", 7)

        process_mock.assert_called_once_with(7)
        publish_mock.assert_called_once_with(7)
        assert result is DeliveryResult.ACKNOWLEDGE
        assert CareerStatsJob.objects.filter(fight_id=7).count() == 2
        assert CareerStatsJob.objects.filter(
            fight_id=7,
            status=CareerStatsJob.Status.COMPLETED,
        ).exists()

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_retries_without_publish(
        self, process_mock: MagicMock, publish_mock: MagicMock
    ) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")

        result = process_career_stats_message("msg-1", 3)

        job = CareerStatsJob.objects.get(fight_id=3)
        assert job.status == CareerStatsJob.Status.RETRYING
        assert job.retry_count == 1
        publish_mock.assert_not_called()
        assert result is DeliveryResult.RETRY

    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.publish_score_fight_job")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.process_career_stats")
    @patch("ufc_data_pipeline.fighters.career_stats.message_processor.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acknowledges_without_publish(
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

        result = process_career_stats_message("msg-max", 4)

        job.refresh_from_db()
        assert job.status == CareerStatsJob.Status.FAILED
        assert job.retry_count == 3
        publish_mock.assert_not_called()
        assert result is DeliveryResult.ACKNOWLEDGE


class CareerStatsResolverTests(TestCase):
    @patch("ufc_data_pipeline.fighters.career_stats.api.resolver.process_career_stats_message")
    def test_valid_payload_delegates_to_processor(
        self, processor_mock: MagicMock
    ) -> None:
        processor_mock.return_value = DeliveryResult.ACKNOWLEDGE

        result = resolve_career_stats_message("msg-1", {"fight_id": 42})

        processor_mock.assert_called_once_with("msg-1", 42)
        assert result is DeliveryResult.ACKNOWLEDGE

    def test_missing_fight_id_raises(self) -> None:
        with self.assertRaisesRegex(PayloadValidationError, "fight_id is required"):
            resolve_career_stats_message("msg-1", {})

    def test_non_positive_fight_id_raises(self) -> None:
        with self.assertRaisesRegex(PayloadValidationError, "positive integer"):
            resolve_career_stats_message("msg-1", {"fight_id": 0})

    def test_bool_fight_id_raises(self) -> None:
        with self.assertRaisesRegex(PayloadValidationError, "not bool"):
            resolve_career_stats_message("msg-1", {"fight_id": True})

    def test_string_fight_id_raises(self) -> None:
        with self.assertRaisesRegex(PayloadValidationError, "must be an integer"):
            resolve_career_stats_message("msg-1", {"fight_id": "42"})


def _push_body(*, payload: dict, message_id: str = "push-msg-1") -> bytes:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return json.dumps(
        {
            "message": {
                "data": data,
                "messageId": message_id,
            },
            "subscription": "projects/demo/subscriptions/demo-sub",
        }
    ).encode("utf-8")


@override_settings(ROOT_URLCONF="ufc_fantasy.career_stats_urls")
class CareerStatsPushViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    @patch("ufc_data_pipeline.fighters.career_stats.api.views.resolve_career_stats_message")
    def test_acknowledge_returns_204(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.ACKNOWLEDGE

        response = self.client.post(
            "/pipeline/pubsub/career-stats/",
            data=_push_body(payload={"fight_id": 42}),
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch("ufc_data_pipeline.fighters.career_stats.api.views.resolve_career_stats_message")
    def test_retry_returns_500(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.RETRY

        response = self.client.post(
            "/pipeline/pubsub/career-stats/",
            data=_push_body(payload={"fight_id": 42}),
            content_type="application/json",
        )

        assert response.status_code == 500

    def test_invalid_payload_returns_204(self) -> None:
        response = self.client.post(
            "/pipeline/pubsub/career-stats/",
            data=b"not-json",
            content_type="application/json",
        )

        assert response.status_code == 204

    def test_invalid_domain_payload_returns_204(self) -> None:
        response = self.client.post(
            "/pipeline/pubsub/career-stats/",
            data=_push_body(payload={"fight_id": 0}),
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch("ufc_data_pipeline.fighters.career_stats.api.views.resolve_career_stats_message")
    def test_unexpected_error_returns_500(self, resolve_mock: MagicMock) -> None:
        resolve_mock.side_effect = RuntimeError("boom")

        response = self.client.post(
            "/pipeline/pubsub/career-stats/",
            data=_push_body(payload={"fight_id": 42}),
            content_type="application/json",
        )

        assert response.status_code == 500
