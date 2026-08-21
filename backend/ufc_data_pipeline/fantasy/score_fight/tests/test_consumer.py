"""Tests for score-fight message processor, resolver, and push view behavior."""

import base64
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from ufc_data_pipeline.fantasy.score_fight.api.resolver import (
    resolve_score_fight_message,
)
from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoringSourceIncompleteError,
    ScoringSourceUnscoreableError,
)
from ufc_data_pipeline.fantasy.score_fight.message_processor import (
    process_score_fight_message,
)
from ufc_data_pipeline.models import ScoreFightJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


class ScoreFightMessageProcessorTests(TestCase):
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_success_marks_completed_and_acknowledges(self, process_mock) -> None:
        result = process_score_fight_message("msg-1", 42)

        job = ScoreFightJob.objects.get(fight_id=42)
        self.assertEqual(job.status, ScoreFightJob.Status.COMPLETED)
        self.assertEqual(job.pubsub_message_id, "msg-1")
        self.assertIsNotNone(job.completed_at)
        process_mock.assert_called_once_with(42)
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_same_message_id_redelivery_after_completed_acknowledges_without_reprocessing(
        self, process_mock
    ) -> None:
        ScoreFightJob.objects.create(
            fight_id=10,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.COMPLETED,
            pubsub_message_id="msg-same",
        )

        result = process_score_fight_message("msg-same", 10)

        process_mock.assert_not_called()
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)
        self.assertEqual(ScoreFightJob.objects.filter(fight_id=10).count(), 1)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_different_message_id_while_running_acknowledges_without_creating(
        self, process_mock
    ) -> None:
        ScoreFightJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RUNNING,
            pubsub_message_id="msg-a",
            lease_expires_at=timezone.now() + timedelta(minutes=5),
        )

        result = process_score_fight_message("msg-b", 6)

        process_mock.assert_not_called()
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)
        self.assertEqual(ScoreFightJob.objects.filter(fight_id=6).count(), 1)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_retrying_job_is_reused_and_completed(self, process_mock) -> None:
        job = ScoreFightJob.objects.create(
            fight_id=5,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary",
            pubsub_message_id="msg-retry",
        )

        result = process_score_fight_message("msg-retry", 5)

        job.refresh_from_db()
        self.assertEqual(job.status, ScoreFightJob.Status.COMPLETED)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "")
        self.assertEqual(ScoreFightJob.objects.filter(fight_id=5).count(), 1)
        process_mock.assert_called_once_with(5)
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_completed_and_failed_jobs_allow_new_runs(self, process_mock) -> None:
        for fight_id, status, old_msg, new_msg in (
            (50, ScoreFightJob.Status.COMPLETED, "msg-c-old", "msg-c-new"),
            (51, ScoreFightJob.Status.FAILED, "msg-f-old", "msg-f-new"),
        ):
            ScoreFightJob.objects.create(
                fight_id=fight_id,
                ran_at=timezone.now(),
                status=status,
                pubsub_message_id=old_msg,
            )

            result = process_score_fight_message(new_msg, fight_id)

            self.assertEqual(
                ScoreFightJob.objects.filter(fight_id=fight_id).count(),
                2,
            )
            self.assertTrue(
                ScoreFightJob.objects.filter(
                    fight_id=fight_id,
                    status=ScoreFightJob.Status.COMPLETED,
                ).exists()
            )
            self.assertIs(result, DeliveryResult.ACKNOWLEDGE)
        self.assertEqual(process_mock.call_count, 2)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.MAX_RETRY_COUNT",
        3,
    )
    def test_retryable_failure_marks_retrying_and_returns_retry(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = ScoringSourceIncompleteError("not ready")

        result = process_score_fight_message("msg-1", 3)

        job = ScoreFightJob.objects.get(fight_id=3)
        self.assertEqual(job.status, ScoreFightJob.Status.RETRYING)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "not ready")
        self.assertIs(result, DeliveryResult.RETRY)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.MAX_RETRY_COUNT",
        3,
    )
    def test_retry_exhaustion_marks_failed_and_acknowledges(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = RuntimeError("still failing")
        job = ScoreFightJob.objects.create(
            fight_id=4,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RETRYING,
            retry_count=2,
            pubsub_message_id="msg-max",
        )

        result = process_score_fight_message("msg-max", 4)

        job.refresh_from_db()
        self.assertEqual(job.status, ScoreFightJob.Status.FAILED)
        self.assertEqual(job.retry_count, 3)
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.message_processor.process_score_fight"
    )
    def test_unscoreable_failure_is_immediately_failed_and_acknowledged(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = ScoringSourceUnscoreableError("no contest")

        result = process_score_fight_message("msg-1", 8)

        job = ScoreFightJob.objects.get(fight_id=8)
        self.assertEqual(job.status, ScoreFightJob.Status.FAILED)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "no contest")
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)


class ScoreFightResolverTests(TestCase):
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api.resolver.process_score_fight_message"
    )
    def test_valid_payload_calls_processor(self, processor_mock: MagicMock) -> None:
        processor_mock.return_value = DeliveryResult.ACKNOWLEDGE

        result = resolve_score_fight_message("msg-1", {"fight_id": 42})

        processor_mock.assert_called_once_with("msg-1", 42)
        self.assertIs(result, DeliveryResult.ACKNOWLEDGE)

    def test_missing_fight_id_raises(self) -> None:
        with self.assertRaises(PayloadValidationError):
            resolve_score_fight_message("msg-1", {})

    def test_non_positive_or_non_integer_fight_id_raises(self) -> None:
        for fight_id in (0, -1, "42", True):
            with self.subTest(fight_id=fight_id):
                with self.assertRaises(PayloadValidationError):
                    resolve_score_fight_message("msg-1", {"fight_id": fight_id})


@override_settings(ROOT_URLCONF="ufc_fantasy.score_fight_urls")
class ScoreFightPushViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def _push_body(self, payload: dict, *, message_id: str = "push-msg-1") -> dict:
        return {
            "message": {
                "messageId": message_id,
                "data": base64.b64encode(json.dumps(payload).encode("utf-8")).decode(
                    "ascii"
                ),
            },
            "subscription": "projects/local-project/subscriptions/score-fight-jobs-sub",
        }

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api.views.resolve_score_fight_message"
    )
    def test_acknowledge_returns_204(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.ACKNOWLEDGE

        response = self.client.post(
            "/pipeline/pubsub/score-fight/",
            data=json.dumps(self._push_body({"fight_id": 42})),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api.views.resolve_score_fight_message"
    )
    def test_retry_returns_500(self, resolve_mock: MagicMock) -> None:
        resolve_mock.return_value = DeliveryResult.RETRY

        response = self.client.post(
            "/pipeline/pubsub/score-fight/",
            data=json.dumps(self._push_body({"fight_id": 42})),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)

    def test_invalid_envelope_returns_204(self) -> None:
        response = self.client.post(
            "/pipeline/pubsub/score-fight/",
            data=b"not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api.views.resolve_score_fight_message"
    )
    def test_invalid_payload_returns_204(self, resolve_mock: MagicMock) -> None:
        resolve_mock.side_effect = PayloadValidationError("fight_id must be an integer")

        response = self.client.post(
            "/pipeline/pubsub/score-fight/",
            data=json.dumps(self._push_body({"fight_id": True})),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)
