from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fantasy", "0039_fight_replay_identity_constraints"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fights",
            name="fight_status",
            field=models.CharField(
                choices=[
                    ("UPCOMING", "Upcoming"),
                    ("COMPLETED", "Completed"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="UPCOMING",
                max_length=16,
            ),
        ),
    ]
