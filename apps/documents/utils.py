import mimetypes
from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils.text import slugify

DEFAULT_DOCUMENT_MIME_TYPE = "application/octet-stream"
BYTES_PER_MEGABYTE = 1024 * 1024

# SEC-008 : types de documents autorises a l'upload (PDF, Word, Images —
# decision du developpeur : pas de PowerPoint). La cle est l'extension
# normalisee, la valeur le type MIME impose cote serveur (jamais celui
# fourni par le client).
ALLOWED_DOCUMENT_UPLOAD_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# Signatures binaires (magic bytes) attendues en tete de fichier, pour
# detecter un fichier dont le contenu ne correspond pas a son extension
# (ex: un .html renomme en .pdf). .docx est un conteneur ZIP (PK\x03\x04) ;
# .doc est un fichier OLE Compound File (legacy Office).
_DOCUMENT_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".docx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}

MAX_DOCUMENT_UPLOAD_SIZE_BYTES = 20 * BYTES_PER_MEGABYTE


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


def validate_document_upload(upload) -> str:
    """Valide la taille et le type reel (signature binaire) d'un fichier
    televerse. Retourne le type MIME impose cote serveur (jamais celui du
    client) si valide, leve ValidationError sinon.
    """
    if upload.size is not None and upload.size > MAX_DOCUMENT_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            {
                "file_path": (
                    "Le fichier depasse la taille maximale autorisee "
                    f"({format_file_size(MAX_DOCUMENT_UPLOAD_SIZE_BYTES)})."
                )
            }
        )

    file_name = Path(getattr(upload, "name", "") or "").name
    extension = Path(file_name).suffix.lower()

    if extension not in ALLOWED_DOCUMENT_UPLOAD_TYPES:
        allowed = ", ".join(sorted(ALLOWED_DOCUMENT_UPLOAD_TYPES))
        raise ValidationError(
            {
                "file_path": (
                    f"Type de fichier non autorise ({extension or 'inconnu'}). "
                    f"Formats acceptes : {allowed}."
                )
            }
        )

    upload.seek(0)
    header = upload.read(8)
    upload.seek(0)

    signatures = _DOCUMENT_SIGNATURES.get(extension, ())
    if signatures and not any(header.startswith(sig) for sig in signatures):
        raise ValidationError(
            {
                "file_path": (
                    "Le contenu du fichier ne correspond pas a son extension "
                    f"({extension}). Le fichier semble corrompu ou usurpe."
                )
            }
        )

    return ALLOWED_DOCUMENT_UPLOAD_TYPES[extension]
