from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fantasy", "0037_fighters_profile_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="fights",
            name="fight_status",
            field=models.CharField(
                choices=[
                    ("UPCOMING", "Upcoming"),
                    ("COMPLETED", "Completed"),
                ],
                default="UPCOMING",
                max_length=16,
            ),
        ),
    ]
