# Generated manually for Live Event Results Watcher lease/state (issue 033).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fantasy", "0039_fight_replay_identity_constraints"),
        ("ufc_data_pipeline", "0007_score_fight_job"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiveEventResultsState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("IDLE", "Idle"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="IDLE",
                        max_length=16,
                    ),
                ),
                ("owner_token", models.UUIDField(blank=True, null=True)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("last_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_completed_at", models.DateTimeField(blank=True, null=True)),
                ("warnings", models.TextField(blank=True, default="")),
                ("last_error", models.TextField(blank=True, default="")),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="live_event_results_state",
                        to="fantasy.events",
                    ),
                ),
            ],
            options={
                "db_table": "live_event_results_state",
            },
        ),
    ]
