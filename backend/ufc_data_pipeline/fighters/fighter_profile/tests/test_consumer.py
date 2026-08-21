"""
Tests for fighter profile message processor and resolver behavior.
"""

import base64
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from ufc_data_pipeline.fighters.fighter_profile.api.resolver import (
    resolve_fighter_profile_message,
)
from ufc_data_pipeline.fighters.fighter_profile.message_processor import (
    process_fighter_profile_message,
)
from ufc_data_pipeline.models import FighterProfileScrapeJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


class FighterProfileMessageProcessorTests(TestCase):
    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
    def test_same_message_id_redelivery_after_completed_acknowledges_without_reprocessing(
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

        result = process_fighter_profile_message("msg-same", 10, fighter_url)

        process_mock.assert_not_called()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert FighterProfileScrapeJob.objects.filter(fighter_id=10).count() == 1

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
    def test_different_message_id_while_running_acknowledges_without_creating(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/running"
        FighterProfileScrapeJob.objects.create(
            fighter_id=6,
            profile_url=fighter_url,
            ran_at=timezone.now(),
            status=FighterProfileScrapeJob.Status.RUNNING,
            pubsub_message_id="msg-a",
            lease_expires_at=timezone.now() + timedelta(minutes=5),
        )

        result = process_fighter_profile_message("msg-b", 6, fighter_url)

        process_mock.assert_not_called()
        assert result is DeliveryResult.ACKNOWLEDGE
        assert FighterProfileScrapeJob.objects.filter(fighter_id=6).count() == 1

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
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

        result = process_fighter_profile_message("msg-new", 1, fighter_url)

        process_mock.assert_called_once_with(1, fighter_url)
        assert result is DeliveryResult.ACKNOWLEDGE
        assert FighterProfileScrapeJob.objects.filter(fighter_id=1).count() == 2

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
    def test_success_creates_running_job_marks_completed_and_acknowledges(
        self, process_mock: MagicMock
    ) -> None:
        fighter_url = "http://ufcstats.com/fighter-details/success"

        result = process_fighter_profile_message("msg-1", 2, fighter_url)

        job = FighterProfileScrapeJob.objects.get(fighter_id=2)
        assert job.status == FighterProfileScrapeJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-1"
        assert job.completed_at is not None
        assert job.profile_url == fighter_url
        process_mock.assert_called_once_with(2, fighter_url)
        assert result is DeliveryResult.ACKNOWLEDGE

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.MAX_RETRY_COUNT", 3)
    def test_retriable_failure_returns_retry(self, process_mock: MagicMock) -> None:
        process_mock.side_effect = RuntimeError("temporary failure")
        fighter_url = "http://ufcstats.com/fighter-details/retry"

        result = process_fighter_profile_message("msg-1", 3, fighter_url)

        job = FighterProfileScrapeJob.objects.get(fighter_id=3)
        assert job.status == FighterProfileScrapeJob.Status.RETRYING
        assert job.retry_count == 1
        assert result is DeliveryResult.RETRY

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.MAX_RETRY_COUNT", 3)
    def test_max_retries_marks_failed_and_acknowledges(self, process_mock: MagicMock) -> None:
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

        result = process_fighter_profile_message("msg-max", 4, fighter_url)

        job.refresh_from_db()
        assert job.status == FighterProfileScrapeJob.Status.FAILED
        assert job.retry_count == 3
        assert result is DeliveryResult.ACKNOWLEDGE

    @patch("ufc_data_pipeline.fighters.fighter_profile.message_processor.process_fighter_profile")
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

        result = process_fighter_profile_message("msg-retry", 5, fighter_url)

        job.refresh_from_db()
        assert job.status == FighterProfileScrapeJob.Status.COMPLETED
        assert job.error_msg == ""
        process_mock.assert_called_once_with(5, fighter_url)
        assert result is DeliveryResult.ACKNOWLEDGE
        assert FighterProfileScrapeJob.objects.filter(fighter_id=5).count() == 1


class FighterProfileResolverTests(TestCase):
    @patch("ufc_data_pipeline.fighters.fighter_profile.api.resolver.process_fighter_profile_message")
    def test_valid_payload_calls_processor(self, processor_mock: MagicMock) -> None:
        processor_mock.return_value = DeliveryResult.ACKNOWLEDGE
        fighter_url = "http://ufcstats.com/fighter-details/valid"

        result = resolve_fighter_profile_message(
            "msg-1",
            {"fighter_id": 7, "fighter_url": f"  {fighter_url}  "},
        )

        processor_mock.assert_called_once_with("msg-1", 7, fighter_url)
        assert result is DeliveryResult.ACKNOWLEDGE

    def test_missing_fighter_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fighter_profile_message(
                "msg-1",
                {"fighter_url": "http://ufcstats.com/fighter-details/x"},
            )

    def test_missing_fighter_url_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fighter_profile_message("msg-1", {"fighter_id": 1})

    def test_invalid_fighter_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fighter_profile_message(
                "msg-1",
                {"fighter_id": "not-int", "fighter_url": "http://example.com"},
            )

    def test_empty_fighter_url_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_fighter_profile_message(
                "msg-1",
                {"fighter_id": 1, "fighter_url": "   "},
            )


@override_settings(ROOT_URLCONF="ufc_fantasy.fighter_profile_urls")
class FighterProfilePushViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def _push_body(self, payload: dict, *, message_id: str = "push-msg-1") -> dict:
        return {
            "message": {
                "messageId": message_id,
                "data": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii"),
            },
            "subscription": "projects/local-project/subscriptions/fighter-profile-jobs-sub",
        }

    @patch("ufc_data_pipeline.fighters.fighter_profile.api.views.resolve_fighter_profile_message")
    def test_acknowledge_returns_204(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.ACKNOWLEDGE

        response = self.client.post(
            "/pipeline/pubsub/fighter-profile/",
            data=json.dumps(self._push_body({"fighter_id": 1, "fighter_url": "http://x"})),
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch("ufc_data_pipeline.fighters.fighter_profile.api.views.resolve_fighter_profile_message")
    def test_retry_returns_500(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.RETRY

        response = self.client.post(
            "/pipeline/pubsub/fighter-profile/",
            data=json.dumps(self._push_body({"fighter_id": 1, "fighter_url": "http://x"})),
            content_type="application/json",
        )

        assert response.status_code == 500

    def test_invalid_envelope_returns_204(self) -> None:
        response = self.client.post(
            "/pipeline/pubsub/fighter-profile/",
            data=b"not-json",
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch("ufc_data_pipeline.fighters.fighter_profile.api.views.resolve_fighter_profile_message")
    def test_invalid_payload_returns_204(self, resolve_mock: MagicMock) -> None:
        resolve_mock.side_effect = PayloadValidationError("fighter_url is empty")

        response = self.client.post(
            "/pipeline/pubsub/fighter-profile/",
            data=json.dumps(self._push_body({"fighter_id": 1, "fighter_url": ""})),
            content_type="application/json",
        )

        assert response.status_code == 204
