"""Tests for shared Pub/Sub job claim helper."""

from datetime import timedelta

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

    def test_new_claim_sets_lease_about_five_minutes_ahead(self) -> None:
        before = timezone.now()
        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m-lease",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )
        after = timezone.now()

        assert job is not None
        assert job.lease_expires_at is not None
        assert before + timedelta(minutes=5) <= job.lease_expires_at
        assert job.lease_expires_at <= after + timedelta(minutes=5)

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
            lease_expires_at=timezone.now() + timedelta(minutes=5),
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

    def test_expired_running_job_is_reclaimed_on_same_row(self) -> None:
        original = FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/old",
            ran_at=timezone.now() - timedelta(minutes=10),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m1",
            retry_count=2,
            error_msg="worker crashed",
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )
        original_ran_at = original.ran_at
        before = timezone.now()

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m2",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/new",
            },
            retry_update_fields={"fight_url": "http://ufcstats.com/fight-details/new"},
        )
        after = timezone.now()

        assert job is not None
        assert job.pk == original.pk
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 1
        assert job.pubsub_message_id == "m2"
        assert job.status == FightStatsScrapeJob.Status.RUNNING
        assert job.fight_url == "http://ufcstats.com/fight-details/new"
        assert job.retry_count == 2
        assert job.error_msg == ""
        assert job.ran_at == original_ran_at
        assert job.lease_expires_at is not None
        assert before + timedelta(minutes=5) <= job.lease_expires_at
        assert job.lease_expires_at <= after + timedelta(minutes=5)

    def test_running_job_with_null_lease_is_reclaimed(self) -> None:
        original = FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m1",
            lease_expires_at=None,
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
        assert job.pk == original.pk
        assert job.pubsub_message_id == "m2"
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 1

    def test_same_message_id_expired_running_job_is_reclaimed(self) -> None:
        original = FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m-same",
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m-same",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert job is not None
        assert job.pk == original.pk
        assert job.pubsub_message_id == "m-same"
        assert job.lease_expires_at is not None
        assert job.lease_expires_at > timezone.now()

    def test_same_message_id_unexpired_running_job_is_skipped(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m-same",
            lease_expires_at=timezone.now() + timedelta(minutes=5),
        )

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m-same",
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

    def test_retrying_job_is_reclaimed_with_fresh_lease(self) -> None:
        original = FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RETRYING,
            retry_count=1,
            error_msg="temporary",
            pubsub_message_id="m1",
        )
        before = timezone.now()

        job = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m2",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/b",
            },
            retry_update_fields={"fight_url": "http://ufcstats.com/fight-details/b"},
        )
        after = timezone.now()

        assert job is not None
        assert job.pk == original.pk
        assert job.status == FightStatsScrapeJob.Status.RUNNING
        assert job.retry_count == 1
        assert job.pubsub_message_id == "m2"
        assert job.fight_url == "http://ufcstats.com/fight-details/b"
        assert job.lease_expires_at is not None
        assert before + timedelta(minutes=5) <= job.lease_expires_at
        assert job.lease_expires_at <= after + timedelta(minutes=5)

    def test_failed_job_allows_new_message_id(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.FAILED,
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

    def test_pending_job_is_skipped_even_with_expired_lease(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.PENDING,
            pubsub_message_id="m1",
            lease_expires_at=timezone.now() - timedelta(minutes=10),
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

    def test_reclaimed_job_blocks_a_later_unexpired_claim(self) -> None:
        FightStatsScrapeJob.objects.create(
            fight_id=1,
            fight_url="http://ufcstats.com/fight-details/a",
            ran_at=timezone.now(),
            status=FightStatsScrapeJob.Status.RUNNING,
            pubsub_message_id="m1",
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )

        first = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m2",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )
        second = claim_pubsub_job(
            model=FightStatsScrapeJob,
            message_id="m3",
            logical_filters={"fight_id": 1},
            create_kwargs={
                "fight_id": 1,
                "fight_url": "http://ufcstats.com/fight-details/a",
            },
        )

        assert first is not None
        assert second is None
        assert FightStatsScrapeJob.objects.filter(fight_id=1).count() == 1

