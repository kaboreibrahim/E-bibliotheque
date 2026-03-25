import uuid

from django.conf import settings
from django.db import models
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.documents.models.document_type_models import TypeDocument
from apps.documents.models.document_ue_models import DocumentUE
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.ue.models import UE
from apps.users.models.user_models import document_file_upload_path


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
    file_path = models.FileField(
        upload_to=document_file_upload_path,
        verbose_name="Fichier",
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

    def __str__(self):
        return f"[{self.type}] {self.title}"
