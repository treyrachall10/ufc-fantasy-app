"""Tests for the score-fight pipeline job model."""

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.models import ScoreFightJob


class ScoreFightJobModelTests(TestCase):
    def test_create_running_job_with_base_defaults(self) -> None:
        job = ScoreFightJob.objects.create(
            fight_id=42,
            ran_at=timezone.now(),
        )

        loaded = ScoreFightJob.objects.get(pk=job.pk)
        self.assertEqual(loaded.fight_id, 42)
        self.assertEqual(loaded.status, ScoreFightJob.Status.RUNNING)
        self.assertEqual(loaded.retry_count, 0)
        self.assertEqual(loaded.error_msg, "")
        self.assertIsNone(loaded.completed_at)

    def test_fight_id_is_raw_and_indexed_with_status(self) -> None:
        fight_id_field = ScoreFightJob._meta.get_field("fight_id")

        self.assertFalse(fight_id_field.is_relation)
        self.assertEqual(
            [index.fields for index in ScoreFightJob._meta.indexes],
            [["fight_id", "status"]],
        )
