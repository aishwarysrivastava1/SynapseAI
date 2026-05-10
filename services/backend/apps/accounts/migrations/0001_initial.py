from django.db import migrations


class Migration(migrations.Migration):
    """
    Fake-initial migration. Tables already exist from SQLAlchemy.
    Run: python manage.py migrate --fake-initial
    
    The RunSQL ops convert PostgreSQL enum columns to VARCHAR so Django
    CharField can manage them without type errors.
    """
    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",  # irreversible — enum type removed
        ),
        migrations.RunSQL(
            sql="ALTER TABLE volunteer_profiles ALTER COLUMN status TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE consent_events ALTER COLUMN scope TYPE VARCHAR(30)",
            reverse_sql="SELECT 1",
        ),
    ]
