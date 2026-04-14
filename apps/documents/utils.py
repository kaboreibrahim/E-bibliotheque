import base64
import binascii
import mimetypes
from pathlib import Path

from django.utils.text import slugify

DEFAULT_DOCUMENT_MIME_TYPE = "application/octet-stream"


def normalize_base64_document(content: str) -> tuple[str, str | None]:
    cleaned_content = (content or "").strip()
    if not cleaned_content:
        raise ValueError("Le contenu Base64 du document est obligatoire.")

    detected_mime_type = None
    if cleaned_content.startswith("data:"):
        header, separator, payload = cleaned_content.partition(",")
        if not separator or ";base64" not in header:
            raise ValueError("Le fichier Base64 doit etre fourni au format data URI valide.")
        detected_mime_type = header[5:].split(";", 1)[0] or DEFAULT_DOCUMENT_MIME_TYPE
        cleaned_content = payload

    cleaned_content = "".join(cleaned_content.split())

    try:
        decoded_content = base64.b64decode(cleaned_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Le contenu Base64 du document est invalide.") from exc

    normalized_content = base64.b64encode(decoded_content).decode("ascii")
    return normalized_content, detected_mime_type


def encode_uploaded_document(uploaded_file) -> tuple[str, str, str]:
    file_name = Path(getattr(uploaded_file, "name", "document")).name or "document"
    mime_type = (
        getattr(uploaded_file, "content_type", "")
        or mimetypes.guess_type(file_name)[0]
        or DEFAULT_DOCUMENT_MIME_TYPE
    )
    encoded_content = base64.b64encode(uploaded_file.read()).decode("ascii")
    return encoded_content, file_name, mime_type


def build_document_data_uri(content_base64: str, mime_type: str | None = None) -> str | None:
    if not content_base64:
        return None
    return f"data:{mime_type or DEFAULT_DOCUMENT_MIME_TYPE};base64,{content_base64}"


def build_document_file_name(title: str, mime_type: str | None = None) -> str:
    extension = mimetypes.guess_extension(mime_type or "") or ""
    if extension == ".jpe":
        extension = ".jpg"
    base_name = slugify(title) or "document"
    return f"{base_name}{extension}"
