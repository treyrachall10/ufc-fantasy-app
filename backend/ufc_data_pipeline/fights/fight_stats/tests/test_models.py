"""Tests for fight stats pipeline job models."""

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.models import FightStatsScrapeJob


class FightStatsScrapeJobModelTests(TestCase):
    def test_create_running_job(self) -> None:
        fight_url = "http://ufcstats.com/fight-details/test-fight"
        job = FightStatsScrapeJob.objects.create(
            fight_id=42,
            fight_url=fight_url,
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
        )

        loaded = FightStatsScrapeJob.objects.get(pk=job.pk)
        assert loaded.fight_id == 42
        assert loaded.fight_url == fight_url
        assert loaded.status == FightStatsScrapeJob.Status.RUNNING
        assert loaded.retry_count == 0
        assert loaded.error_msg == ""
