"""Tests for shared Pub/Sub job claim helper."""

from django.test import TestCase
from django.utils import timezone

from ufc_data_pipeline.models import FightStatsScrapeJob
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job


class ClaimPubsubJobTests(TestCase):
    def test_creates_new_job_with_message_id(self) -> None:
        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m1",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert job is not None
        assert job.pubsub_message_id == "m1"
        assert job.status == FightStatsScrapeJob.Status.RUNNING

    def test_same_message_id_completed_returns_none(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.COMPLETED,
            pubsub_message_id="m1",
        )

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m1",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert job is None
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 1

    def test_different_message_id_while_running_returns_none(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m1",
        )

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m2",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert job is None
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 1

    def test_completed_allows_new_message_id(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.COMPLETED,
            pubsub_message_id="m1",
        )

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m2",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert job is not None
        assert job.pubsub_message_id == "m2"
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 2
