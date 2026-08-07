# Generated manually for fighter profile decouple phase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ufc_data_pipeline', '0003_fighterprofilescrapejob_alter_status_pending'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fighterprofilescrapejob',
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
    ]
