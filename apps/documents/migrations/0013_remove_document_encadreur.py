from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_fix_document_file_path_column_length"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="document",
            name="encadreur",
        ),
    ]
