from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ufc_data_pipeline", "0011_pubsub_message_id_active_job_constraints"),
    ]

    operations = [
        migrations.AddField(
            model_name="careerstatsjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="eventsyncjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fightcreationjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fighterprofilescrapejob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fightstatsscrapejob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="scorefightjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
