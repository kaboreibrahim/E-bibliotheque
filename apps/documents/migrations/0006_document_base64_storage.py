import base64
import binascii
import mimetypes
import os

from django.core.files.storage import default_storage
from django.db import migrations, models


def _normalize_possible_base64(value: str) -> str | None:
    cleaned_value = "".join((value or "").split())
    if not cleaned_value:
        return None

    try:
        decoded_value = base64.b64decode(cleaned_value, validate=True)
    except (binascii.Error, ValueError):
        return None

    return base64.b64encode(decoded_value).decode("ascii")


def convert_document_files_to_base64(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    db_alias = schema_editor.connection.alias

    for document in Document.objects.using(db_alias).all().iterator():
        stored_value = (document.file_base64 or "").strip()
        file_name = os.path.basename(stored_value) if stored_value else ""
        mime_type = mimetypes.guess_type(file_name)[0] or ""

        if stored_value and default_storage.exists(stored_value):
            with default_storage.open(stored_value, "rb") as source_file:
                encoded_value = base64.b64encode(source_file.read()).decode("ascii")
            document.file_base64 = encoded_value
            document.file_name = file_name
            document.file_mime_type = mime_type
            document.save(
                update_fields=["file_base64", "file_name", "file_mime_type"],
                using=db_alias,
            )
            continue

        normalized_value = _normalize_possible_base64(stored_value)
        if normalized_value:
            document.file_base64 = normalized_value
            if not document.file_name:
                document.file_name = file_name or "document"
            if not document.file_mime_type:
                document.file_mime_type = mime_type or "application/octet-stream"
            document.save(
                update_fields=["file_base64", "file_name", "file_mime_type"],
                using=db_alias,
            )
            continue

        document.file_base64 = base64.b64encode(stored_value.encode("utf-8")).decode("ascii")
        document.file_name = file_name or "document.txt"
        document.file_mime_type = mime_type or "text/plain"
        document.save(
            update_fields=["file_base64", "file_name", "file_mime_type"],
            using=db_alias,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_document_annee_academique_debut"),
    ]

    operations = [
        migrations.RenameField(
            model_name="document",
            old_name="file_path",
            new_name="file_base64",
        ),
        migrations.AlterField(
            model_name="document",
            name="file_base64",
            field=models.TextField(verbose_name="Fichier encode en Base64"),
        ),
        migrations.AddField(
            model_name="document",
            name="file_name",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Nom du fichier"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="document",
            name="file_mime_type",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Type MIME"),
            preserve_default=False,
        ),
        migrations.RunPython(convert_document_files_to_base64, migrations.RunPython.noop),
    ]
