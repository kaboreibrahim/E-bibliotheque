import mimetypes
from pathlib import Path

from django.utils.text import slugify

DEFAULT_DOCUMENT_MIME_TYPE = "application/octet-stream"
BYTES_PER_MEGABYTE = 1024 * 1024


def _build_storage_segment(value: str | None, fallback: str) -> str:
    normalized = slugify(str(value or "").strip())
    return normalized or fallback


def document_upload_path(instance, filename: str) -> str:
    filiere_name = getattr(getattr(instance, "filiere", None), "name", None)
    document_type = getattr(instance, "type", None)
    document_type_label = (
        getattr(document_type, "name", None)
        or getattr(document_type, "code", None)
        or "AUTRE"
    )
    niveau_name = getattr(getattr(instance, "niveau", None), "name", None)
    specialite_name = getattr(getattr(instance, "specialite", None), "name", None)
    academic_year = getattr(instance, "annee_academique", None)
    safe_name = Path(filename or "document").name or "document"

    return "/".join(
        [
            "documents",
            _build_storage_segment(filiere_name, "sans-filiere"),
            _build_storage_segment(document_type_label, "autre"),
            _build_storage_segment(niveau_name, "sans-niveau"),
            _build_storage_segment(specialite_name, "sans-specialite"),
            _build_storage_segment(academic_year, "sans-annee-scolaire"),
            safe_name,
        ]
    )


def extract_document_file_metadata(uploaded_file) -> tuple[str, str]:
    file_name = Path(getattr(uploaded_file, "name", "document")).name or "document"
    mime_type = (
        getattr(uploaded_file, "content_type", "")
        or mimetypes.guess_type(file_name)[0]
        or DEFAULT_DOCUMENT_MIME_TYPE
    )
    return file_name, mime_type


def build_document_file_name(title: str, mime_type: str | None = None) -> str:
    extension = mimetypes.guess_extension(mime_type or "") or ""
    if extension == ".jpe":
        extension = ".jpg"
    base_name = slugify(title) or "document"
    return f"{base_name}{extension}"


def format_file_size(size: int | None) -> str:
    if not size:
        return "0 octets"

    if size < 1024:
        unit = "octet" if size == 1 else "octets"
        return f"{size} {unit}"

    value = float(size)
    units = ("Ko", "Mo", "Go", "To")
    for unit in units:
        value /= 1024
        if value < 1024 or unit == units[-1]:
            formatted_value = f"{value:.2f}".rstrip("0").rstrip(".")
            return f"{formatted_value} {unit}"

    return f"{size} octets"


def bytes_to_megabytes(size: int | None) -> float:
    if not size:
        return 0.0
    return round(size / BYTES_PER_MEGABYTE, 2)
