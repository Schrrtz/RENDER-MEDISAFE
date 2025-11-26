from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0013_appointment_duration_minutes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='prescription',
            name='doctor',
            field=models.ForeignKey(blank=True, db_column='doctor_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prescriptions_made', to='myapp.doctor'),
        ),
    ]
