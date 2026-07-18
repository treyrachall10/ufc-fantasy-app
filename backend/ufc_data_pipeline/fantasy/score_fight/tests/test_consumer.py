"""Tests for score-fight Pub/Sub consumer behavior."""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.fantasy.score_fight import consumer
from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoringSourceIncompleteError,
    ScoringSourceUnscoreableError,
)
from ufc_data_pipeline.models import ScoreFightJob


class ScoreFightConsumerTests(TestCase):
    def _message(self, payload: dict) -> MagicMock:
        message = MagicMock()
        message.data = json.dumps(payload).encode("utf-8")
        return message

    def test_invalid_payload_is_acked_without_job(self) -> None:
        message = MagicMock()
        message.data = b"not-json"

        consumer.callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(ScoreFightJob.objects.count(), 0)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    def test_success_marks_completed_before_ack(self, process_mock) -> None:
        message = self._message({"fight_id": 42})
        status_at_ack: list[str] = []

        def capture_status() -> None:
            status_at_ack.append(
                ScoreFightJob.objects.get(fight_id=42).status
            )

        message.ack.side_effect = capture_status

        consumer.callback(message)

        job = ScoreFightJob.objects.get(fight_id=42)
        self.assertEqual(job.status, ScoreFightJob.Status.COMPLETED)
        self.assertIsNotNone(job.completed_at)
        process_mock.assert_called_once_with(42)
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(status_at_ack, [ScoreFightJob.Status.COMPLETED])

    def test_non_positive_or_non_integer_fight_id_is_acked(self) -> None:
        for fight_id in (0, -1, "42", True):
            with self.subTest(fight_id=fight_id):
                message = self._message({"fight_id": fight_id})
                consumer.callback(message)
                message.ack.assert_called_once()
                message.nack.assert_not_called()
        self.assertEqual(ScoreFightJob.objects.count(), 0)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    def test_running_job_is_skipped_and_acked(self, process_mock) -> None:
        ScoreFightJob.objects.create(
            fight_id=6,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RUNNING,
        )
        message = self._message({"fight_id": 6})

        consumer.callback(message)

        process_mock.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()
        self.assertEqual(ScoreFightJob.objects.filter(fight_id=6).count(), 1)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    def test_retrying_job_is_reused_and_completed(self, process_mock) -> None:
        job = ScoreFightJob.objects.create(
            fight_id=5,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary",
        )
        message = self._message({"fight_id": 5})

        consumer.callback(message)

        job.refresh_from_db()
        self.assertEqual(job.status, ScoreFightJob.Status.COMPLETED)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "")
        self.assertEqual(ScoreFightJob.objects.filter(fight_id=5).count(), 1)
        process_mock.assert_called_once_with(5)
        message.ack.assert_called_once()

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    def test_completed_and_failed_jobs_allow_new_runs(self, process_mock) -> None:
        for fight_id, status in (
            (50, ScoreFightJob.Status.COMPLETED),
            (51, ScoreFightJob.Status.FAILED),
        ):
            ScoreFightJob.objects.create(
                fight_id=fight_id,
                ran_at=timezone.now(),
                status=status,
            )
            message = self._message({"fight_id": fight_id})

            consumer.callback(message)

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
            message.ack.assert_called_once()
        self.assertEqual(process_mock.call_count, 2)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.MAX_RETRY_COUNT",
        3,
    )
    def test_retryable_failure_marks_retrying_and_nacks(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = ScoringSourceIncompleteError("not ready")
        message = self._message({"fight_id": 3})

        consumer.callback(message)

        job = ScoreFightJob.objects.get(fight_id=3)
        self.assertEqual(job.status, ScoreFightJob.Status.RETRYING)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "not ready")
        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.MAX_RETRY_COUNT",
        3,
    )
    def test_retry_exhaustion_marks_failed_and_acks(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = RuntimeError("still failing")
        job = ScoreFightJob.objects.create(
            fight_id=4,
            ran_at=timezone.now(),
            status=ScoreFightJob.Status.RETRYING,
            retry_count=2,
        )
        message = self._message({"fight_id": 4})

        consumer.callback(message)

        job.refresh_from_db()
        self.assertEqual(job.status, ScoreFightJob.Status.FAILED)
        self.assertEqual(job.retry_count, 3)
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.process_score_fight"
    )
    def test_unscoreable_failure_is_immediately_failed_and_acked(
        self,
        process_mock,
    ) -> None:
        process_mock.side_effect = ScoringSourceUnscoreableError("no contest")
        message = self._message({"fight_id": 8})

        consumer.callback(message)

        job = ScoreFightJob.objects.get(fight_id=8)
        self.assertEqual(job.status, ScoreFightJob.Status.FAILED)
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_msg, "no contest")
        message.ack.assert_called_once()
        message.nack.assert_not_called()
