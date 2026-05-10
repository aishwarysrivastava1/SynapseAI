from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL(sql="SELECT 1", reverse_sql="SELECT 1"),
    ]
