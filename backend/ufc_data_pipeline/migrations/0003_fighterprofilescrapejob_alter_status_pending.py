# Generated manually for fighter profile scraper phase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ufc_data_pipeline', '0002_alter_eventsyncjob_status_fightcreationjob'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventsyncjob',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('RUNNING', 'Running'),
                    ('COMPLETED', 'Completed'),
                    ('RETRYING', 'Retrying'),
                    ('FAILED', 'Failed'),
                ],
                default='RUNNING',
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name='fightcreationjob',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('RUNNING', 'Running'),
                    ('COMPLETED', 'Completed'),
                    ('RETRYING', 'Retrying'),
                    ('FAILED', 'Failed'),
                ],
                default='RUNNING',
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name='FighterProfileScrapeJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ran_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'),
                        ('RUNNING', 'Running'),
                        ('COMPLETED', 'Completed'),
                        ('RETRYING', 'Retrying'),
                        ('FAILED', 'Failed'),
                    ],
                    default='PENDING',
                    max_length=16,
                )),
                ('error_msg', models.TextField(blank=True, default='')),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('fighter_id', models.PositiveIntegerField()),
                ('profile_url', models.CharField(max_length=512)),
            ],
            options={
                'db_table': 'fighter_profile_scrape_job',
                'indexes': [
                    models.Index(fields=['fighter_id', 'status'], name='fighter_pro_fighter_8a1b2c_idx'),
                ],
            },
        ),
    ]
