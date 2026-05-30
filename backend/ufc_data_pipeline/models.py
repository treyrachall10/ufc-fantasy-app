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
        default=BaseJobModel.Status.PENDING,
    )

    class Meta:
        db_table = "fighter_profile_scrape_job"
        indexes = [
            models.Index(fields=["fighter_id", "status"]),
        ]
