# Generated manually for Live Fight Stats handoffs (issue 035).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ufc_data_pipeline", "0008_live_event_results_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiveFightStatsHandoff",
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
                ("fight_id", models.PositiveIntegerField(unique=True)),
                ("event_id", models.PositiveIntegerField()),
                ("fight_url", models.CharField(max_length=512)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PUBLISHED", "Published"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
            ],
            options={
                "db_table": "live_fight_stats_handoff",
            },
        ),
        migrations.AddIndex(
            model_name="livefightstatshandoff",
            index=models.Index(
                fields=["event_id", "status"],
                name="live_fight__event_i_7c8a1d_idx",
            ),
        ),
    ]
