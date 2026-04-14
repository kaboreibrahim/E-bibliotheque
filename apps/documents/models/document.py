import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.documents.models.document_type_models import TypeDocument
from apps.documents.models.document_ue_models import DocumentUE
from apps.documents.utils import (
    DEFAULT_DOCUMENT_MIME_TYPE,
    build_document_data_uri,
    build_document_file_name,
    normalize_base64_document,
)


class Document(DocumentUE, SafeDeleteModel):
    """Document principal de la bibliotheque."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Titre")
    type = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
        verbose_name="Type de document",
    )
    file_base64 = models.TextField(
        verbose_name="Fichier encode en Base64",
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
        return bool(self.file_base64)

    @property
    def file_data_uri(self) -> str | None:
        return build_document_data_uri(self.file_base64, self.file_mime_type)

    def clean(self):
        super().clean()

        if not self.file_base64:
            raise ValidationError({"file_base64": "Le contenu Base64 du document est obligatoire."})

        try:
            normalized_base64, detected_mime_type = normalize_base64_document(self.file_base64)
        except ValueError as exc:
            raise ValidationError({"file_base64": str(exc)}) from exc

        self.file_base64 = normalized_base64
        if not self.file_mime_type:
            self.file_mime_type = detected_mime_type or DEFAULT_DOCUMENT_MIME_TYPE
        if not self.file_name:
            self.file_name = build_document_file_name(self.title, self.file_mime_type)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.type}] {self.title}"
