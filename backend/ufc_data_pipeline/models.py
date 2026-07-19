from django.db import models

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


class FighterProfileScrapeJob(BaseJobModel):
    """Tracks a UFC Stats fighter profile scrape run."""

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


class FightStatsScrapeJob(BaseJobModel):
    """Tracks a UFC Stats fight detail stats scrape run."""

    fight_id = models.PositiveIntegerField()
    fight_url = models.CharField(max_length=512)

    class Meta:
        db_table = "fight_stats_scrape_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
        ]


class CareerStatsJob(BaseJobModel):
    """Tracks a fighter career-stats recalculation run triggered by a fight."""

    fight_id = models.PositiveIntegerField()

    class Meta:
        db_table = "career_stats_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
        ]


class ScoreFightJob(BaseJobModel):
    """Tracks one fantasy scoring run for a fight."""

    fight_id = models.PositiveIntegerField()

    class Meta:
        db_table = "score_fight_job"
        indexes = [
            models.Index(fields=["fight_id", "status"]),
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
