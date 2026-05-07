from django.db import models

class BaseJobModel(models.Model):
    """Base model for all job models."""
    class Status(models.TextChoices):
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
    """Tracks a UFC Stats fights creation run."""
    class Meta:
        db_table = "fight_creation_job"
