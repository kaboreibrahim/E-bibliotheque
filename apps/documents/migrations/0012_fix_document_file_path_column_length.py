from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_documentstorageconfiguration"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE documents_document "
                "ALTER COLUMN file_path TYPE varchar(1024);"
            ),
            reverse_sql=(
                "ALTER TABLE documents_document "
                "ALTER COLUMN file_path TYPE varchar(100);"
            ),
        ),
    ]
