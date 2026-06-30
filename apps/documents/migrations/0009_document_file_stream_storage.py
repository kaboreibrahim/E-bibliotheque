import base64
import binascii
import mimetypes
import os

import apps.documents.utils
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations, models
from django.utils.text import slugify


DEFAULT_DOCUMENT_MIME_TYPE = "application/octet-stream"


def _decode_possible_base64(value: str) -> tuple[bytes | None, str | None]:
    cleaned_value = (value or "").strip()
    if not cleaned_value:
        return None, None

    detected_mime_type = None
    if cleaned_value.startswith("data:"):
        header, separator, payload = cleaned_value.partition(",")
        if separator and ";base64" in header:
            detected_mime_type = header[5:].split(";", 1)[0] or None
            cleaned_value = payload

    cleaned_value = "".join(cleaned_value.split())
    if not cleaned_value:
        return None, detected_mime_type

    try:
        return base64.b64decode(cleaned_value, validate=True), detected_mime_type
    except (binascii.Error, ValueError):
        return None, detected_mime_type


def _build_storage_path(document, file_name: str) -> str:
    filiere_name = getattr(getattr(document, "filiere", None), "name", None)
    document_type = getattr(document, "type", None)
    document_type_label = (
        getattr(document_type, "name", None)
        or getattr(document_type, "code", None)
        or "AUTRE"
    )
    niveau_name = getattr(getattr(document, "niveau", None), "name", None)
    specialite_name = getattr(getattr(document, "specialite", None), "name", None)
    academic_year = (
        f"{document.annee_academique_debut}-{document.annee_academique_debut + 1}"
        if document.annee_academique_debut is not None
        else None
    )
    safe_name = os.path.basename(file_name or "document") or "document"

    def segment(value, fallback):
        normalized = slugify(str(value or "").strip())
        return normalized or fallback

    return "/".join(
        [
            "documents",
            segment(filiere_name, "sans-filiere"),
            segment(document_type_label, "autre"),
            segment(niveau_name, "sans-niveau"),
            segment(specialite_name, "sans-specialite"),
            segment(academic_year, "sans-annee-scolaire"),
            safe_name,
        ]
    )


def convert_base64_documents_to_files(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    db_alias = schema_editor.connection.alias

    for document in (
        Document.objects.using(db_alias)
        .select_related("type", "filiere", "niveau", "specialite")
        .all()
        .iterator()
    ):
        if getattr(document, "file_path", ""):
            continue

        stored_value = (document.file_base64 or "").strip()
        file_name = (document.file_name or "").strip()
        mime_type = (document.file_mime_type or "").strip()
        file_content = None
        detected_mime_type = None

        if stored_value and default_storage.exists(stored_value):
            with default_storage.open(stored_value, "rb") as source_file:
                file_content = source_file.read()
            if not file_name:
                file_name = os.path.basename(stored_value)
            if not mime_type:
                mime_type = mimetypes.guess_type(file_name)[0] or ""
        else:
            file_content, detected_mime_type = _decode_possible_base64(stored_value)
            if file_content is None:
                file_content = stored_value.encode("utf-8")

        if not file_name:
            extension = mimetypes.guess_extension(mime_type or detected_mime_type or "") or ".bin"
            file_name = f"document-{document.pk}{extension}"

        storage_path = default_storage.save(
            _build_storage_path(document, file_name),
            ContentFile(file_content),
        )
        document.file_path = storage_path
        document.file_name = os.path.basename(storage_path)
        document.file_mime_type = (
            mime_type
            or detected_mime_type
            or mimetypes.guess_type(document.file_name)[0]
            or DEFAULT_DOCUMENT_MIME_TYPE
        )
        document.save(
            update_fields=["file_path", "file_name", "file_mime_type"],
            using=db_alias,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0008_document_type_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="file_path",
            field=models.FileField(
                blank=True,
                max_length=1024,
                null=True,
                upload_to=apps.documents.utils.document_upload_path,
                verbose_name="Fichier",
            ),
        ),
        migrations.RunPython(
            convert_base64_documents_to_files,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="document",
            name="file_base64",
        ),
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
