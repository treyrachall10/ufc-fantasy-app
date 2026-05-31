# Generated manually for fight stats scraper slice 001

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ufc_data_pipeline", "0004_alter_fighterprofilescrapejob_status_default"),
    ]

    operations = [
        migrations.CreateModel(
            name="FightStatsScrapeJob",
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
                ("fight_url", models.CharField(max_length=512)),
            ],
            options={
                "db_table": "fight_stats_scrape_job",
                "indexes": [
                    models.Index(
                        fields=["fight_id", "status"],
                        name="fight_stats_fight_i_6f3a2b_idx",
                    ),
                ],
            },
        ),
    ]
