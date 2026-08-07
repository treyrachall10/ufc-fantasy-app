# Generated manually for Live Event Rescrape handoffs (issue 037).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ufc_data_pipeline", "0009_live_fight_stats_handoff"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiveEventRescrapeHandoff",
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
                ("event_id", models.PositiveIntegerField()),
                ("card_fingerprint", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PUBLISHED", "Published"),
                            ("RESOLVED", "Resolved"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("CARD_CHANGED", "Card changed"),
                            ("MISSING_FIGHT", "Missing fight"),
                            ("MALFORMED_IDENTITY", "Malformed identity"),
                        ],
                        default="CARD_CHANGED",
                        max_length=32,
                    ),
                ),
                ("publication_count", models.PositiveIntegerField(default=0)),
                ("last_published_at", models.DateTimeField(blank=True, null=True)),
                ("next_eligible_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
            ],
            options={
                "db_table": "live_event_rescrape_handoff",
            },
        ),
        migrations.AddConstraint(
            model_name="liveeventrescrapehandoff",
            constraint=models.UniqueConstraint(
                fields=("event_id", "card_fingerprint"),
                name="unique_live_event_rescrape_fingerprint",
            ),
        ),
        migrations.AddIndex(
            model_name="liveeventrescrapehandoff",
            index=models.Index(
                fields=["event_id", "status"],
                name="live_event__event_i_7c2a1b_idx",
            ),
        ),
    ]
