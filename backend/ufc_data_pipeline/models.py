from django.db import models


class EventSyncJob(models.Model):
    """Tracks a UFC Stats completed-events listing scrape/sync run."""

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        RETRYING = "RETRYING", "Retrying"

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
        db_table = "event_sync_job"
