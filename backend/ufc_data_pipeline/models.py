from django.db import models
from django.db.models import Q


class BaseJobModel(models.Model):
    """Base model for all job models."""
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        RETRYING = "RETRYING", "Retrying"
        FAILED = "FAILED", "Failed"

    ran_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    error_msg = models.TextField(blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


_ACTIVE_JOB_STATUS_Q = Q(status__in=["PENDING", "RUNNING", "RETRYING"])


class EventSyncJob(BaseJobModel):
    """Tracks a UFC Stats completed-events listing scrape/sync run."""
    class Meta:
        db_table = "event_sync_job"


class FightCreationJob(BaseJobModel):
    """Tracks a UFC Stats fights creation run (one Pub/Sub delivery per logical job)."""

    pubsub_message_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="GCP Pub/Sub message_id so redeliveries update the same row.",
    )
    event = models.ForeignKey(
        "fantasy.Events",
        on_delete=models.CASCADE,
        related_name="fight_creation_jobs",
    )
    url = models.CharField(max_length=512)

    class Meta:
        db_table = "fight_creation_job"
        constraints = [
            models.UniqueConstraint(
                fields=["event_id"],
                condition=_ACTIVE_JOB_STATUS_Q,
                name="uniq_fight_creation_active_event",
            ),
        ]


class FighterProfileScrapeJob(BaseJobModel):
    """Tracks a UFC Stats fighter profile scrape run."""

    pubsub_message_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="GCP Pub/Sub message_id so redeliveries map to one job row.",
    )
    fighter_id = models.PositiveIntegerField()
    profile_url = models.CharField(max_length=512)
    status = models.CharField(
        max_length=16,
        choices=BaseJobModel.Status.choices,
        default=BaseJobModel.Status.RUNNING,
    )

    class Meta:
        db_table = "fighter_profile_scrape_job"
        indexes = [
            models.Index(fields=["fighter_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["fighter_id"],
                condition=_ACTIVE_JOB_STATUS_Q,
                name="uniq_fighter_profile_active_fighter",
            ),
        ]


class FightStatsScrapeJob(BaseJobModel):
    """Tracks a UFC Stats fight detail stats scrape run."""

    pubsub_message_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="GCP Pub/Sub message_id so redeliveries map to one job row.",
    )
    fight_id = models.PositiveIntegerField()
    fight_url = models.CharField(max_length=512)

    class Meta:
        db_table = "fight_stats_scrape_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["fight_id"],
                condition=_ACTIVE_JOB_STATUS_Q,
                name="uniq_fight_stats_active_fight",
            ),
        ]


class CareerStatsJob(BaseJobModel):
    """Tracks a fighter career-stats recalculation run triggered by a fight."""

    pubsub_message_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="GCP Pub/Sub message_id so redeliveries map to one job row.",
    )
    fight_id = models.PositiveIntegerField()

    class Meta:
        db_table = "career_stats_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["fight_id"],
                condition=_ACTIVE_JOB_STATUS_Q,
                name="uniq_career_stats_active_fight",
            ),
        ]


class ScoreFightJob(BaseJobModel):
    """Tracks one fantasy scoring run for a fight."""

    pubsub_message_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="GCP Pub/Sub message_id so redeliveries map to one job row.",
    )
    fight_id = models.PositiveIntegerField()

    class Meta:
        db_table = "score_fight_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["fight_id"],
                condition=_ACTIVE_JOB_STATUS_Q,
                name="uniq_score_fight_active_fight",
            ),
        ]


class LiveEventResultsState(models.Model):
    """Pipeline-owned lease and durable run state for one event's live results watcher."""

    class Status(models.TextChoices):
        IDLE = "IDLE", "Idle"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    event = models.OneToOneField(
        "fantasy.Events",
        on_delete=models.CASCADE,
        related_name="live_event_results_state",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IDLE,
    )
    owner_token = models.UUIDField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_completed_at = models.DateTimeField(null=True, blank=True)
    warnings = models.TextField(blank=True, default="")
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "live_event_results_state"


class LiveFightStatsHandoff(models.Model):
    """Durable Fight Stats publication handoff for one completed live-result fight."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"

    fight_id = models.PositiveIntegerField(unique=True)
    event_id = models.PositiveIntegerField()
    fight_url = models.CharField(max_length=512)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "live_fight_stats_handoff"
        indexes = [
            models.Index(fields=["event_id", "status"]),
        ]


class LiveEventRescrapeHandoff(models.Model):
    """Durable Fights In Event rescrape handoff for one event card fingerprint."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PUBLISHED = "PUBLISHED", "Published"
        RESOLVED = "RESOLVED", "Resolved"
        FAILED = "FAILED", "Failed"

    class Reason(models.TextChoices):
        CARD_CHANGED = "CARD_CHANGED", "Card changed"
        MISSING_FIGHT = "MISSING_FIGHT", "Missing fight"
        MALFORMED_IDENTITY = "MALFORMED_IDENTITY", "Malformed identity"

    event_id = models.PositiveIntegerField()
    card_fingerprint = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reason = models.CharField(
        max_length=32,
        choices=Reason.choices,
        default=Reason.CARD_CHANGED,
    )
    publication_count = models.PositiveIntegerField(default=0)
    last_published_at = models.DateTimeField(null=True, blank=True)
    next_eligible_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "live_event_rescrape_handoff"
        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "card_fingerprint"],
                name="unique_live_event_rescrape_fingerprint",
            )
        ]
        indexes = [
            models.Index(fields=["event_id", "status"]),
        ]
