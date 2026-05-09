from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fantasy", "0036_fights_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="fighters",
            name="profile_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="UFC Stats fighter detail page URL (for profile sync jobs).",
                max_length=512,
            ),
        ),
    ]
