# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_liveappointment_prescription'),
    ]

    operations = [
        # Add indexes for frequently queried fields
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date ON appointments(doctor_id, consultation_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_doctor_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_patient;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);",
            reverse_sql="DROP INDEX IF EXISTS idx_appointments_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_lab_results_user_date ON lab_results(user_id, upload_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_lab_results_user_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_live_appointments_appointment ON live_appointments(appointment_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_live_appointments_appointment;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_live_appointments_status ON live_appointments(status);",
            reverse_sql="DROP INDEX IF EXISTS idx_live_appointments_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_users_role_active;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_profiles_user;"
        ),
    ]

