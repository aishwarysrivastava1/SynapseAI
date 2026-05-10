from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE chatbot_messages ALTER COLUMN role TYPE VARCHAR(20)",
            reverse_sql="SELECT 1",
        ),
    ]
