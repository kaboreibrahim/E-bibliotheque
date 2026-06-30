import apps.documents.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0009_document_file_stream_storage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="file_path",
            field=models.FileField(
                max_length=1024,
                upload_to=apps.documents.utils.document_upload_path,
                verbose_name="Fichier",
            ),
        ),
    ]
