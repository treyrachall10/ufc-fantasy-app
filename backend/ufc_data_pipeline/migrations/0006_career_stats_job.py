# Generated manually for career stats worker slice 009

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ufc_data_pipeline", "0005_fight_stats_scrape_job"),
    ]

    operations = [
        migrations.CreateModel(
            name="CareerStatsJob",
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
                ("ran_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("RETRYING", "Retrying"),
                            ("FAILED", "Failed"),
                        ],
                        default="RUNNING",
                        max_length=16,
                    ),
                ),
                ("error_msg", models.TextField(blank=True, default="")),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("fight_id", models.PositiveIntegerField()),
            ],
            options={
                "db_table": "career_stats_job",
                "indexes": [
                    models.Index(
                        fields=["fight_id", "status"],
                        name="career_stat_fight_i_a1b2c3_idx",
                    ),
                ],
            },
        ),
    ]
