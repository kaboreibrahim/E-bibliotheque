import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.documents.models.document_type_models import TypeDocument
from apps.documents.models.document_ue_models import DocumentUE
from apps.documents.utils import (
    DEFAULT_DOCUMENT_MIME_TYPE,
    build_document_file_name,
    document_upload_path,
    extract_document_file_metadata,
)


class Document(DocumentUE, SafeDeleteModel):
    """Document principal de la bibliotheque."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Titre")
    type = models.ForeignKey(
        TypeDocument,
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name="Type de document",
    )
    file_path = models.FileField(
        upload_to=document_upload_path,
        max_length=1024,
        verbose_name="Fichier",
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom du fichier",
    )
    file_mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Type MIME",
    )
    description = models.TextField(blank=True, verbose_name="Description")

    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents_ajoutes",
        verbose_name="Ajoute par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajoute le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-created_at"]

    @property
    def has_file_content(self) -> bool:
        return bool(self.file_path)

    @property
    def file_size(self) -> int | None:
        if not self.file_path:
            return None

        try:
            return self.file_path.size
        except (FileNotFoundError, OSError, ValueError):
            return None

    def clean(self):
        if not self.type_id:
            raise ValidationError({"type": "Le type de document est obligatoire."})

        super().clean()

        if not self.file_path:
            raise ValidationError({"file_path": "Le fichier du document est obligatoire."})

        detected_file_name, detected_mime_type = extract_document_file_metadata(self.file_path)

        if self.file_name:
            self.file_name = Path(self.file_name).name
        else:
            self.file_name = detected_file_name

        if not self.file_name:
            self.file_name = build_document_file_name(self.title, self.file_mime_type)

        if not self.file_mime_type:
            self.file_mime_type = detected_mime_type or DEFAULT_DOCUMENT_MIME_TYPE

    @property
    def type_code(self) -> str:
        return TypeDocument.get_code(self.type)

    def get_type_display(self) -> str:
        return TypeDocument.get_display(self.type)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"
