"""Tests for career stats pipeline job models."""

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.models import CareerStatsJob


class CareerStatsJobModelTests(TestCase):
    def test_create_running_job(self) -> None:
        job = CareerStatsJob.objects.create(
            fight_id=42,
            ran_at=timezone.now(),
            status=CareerStatsJob.Status.RUNNING,
        )

        loaded = CareerStatsJob.objects.get(pk=job.pk)
        assert loaded.fight_id == 42
        assert loaded.status == CareerStatsJob.Status.RUNNING
        assert loaded.retry_count == 0
        assert loaded.error_msg == ""
        assert loaded.completed_at is None
