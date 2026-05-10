from django.db import migrations


class Migration(migrations.Migration):
    """Fake-initial: converts remaining PostgreSQL enum columns to VARCHAR."""
    initial = True
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE tasks ALTER COLUMN priority TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tasks ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE assignments ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE resources ALTER COLUMN availability_status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE allocations ALTER COLUMN allocation_status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE events ALTER COLUMN event_type TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE events ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE event_attendance ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE notifications ALTER COLUMN type TYPE VARCHAR(30)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE task_enrollment_requests ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
    ]
