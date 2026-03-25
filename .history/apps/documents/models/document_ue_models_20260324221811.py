from django.core.exceptions import ValidationError
from django.db import models

from apps.documents.models.document_type_models import TypeDocument


class DocumentUEMixin(models.Model):
    """
    Champs metier lies au schema Document_UE.

    - `auteur` est attendu surtout pour memoirs/theses.
    - `encadreur` est attendu surtout pour cours/examens.
    """

    auteur = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Auteur",
        help_text="Pour Memoire et These.",
    )
    encadreur = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Encadreur / Sujet",
        help_text="Pour Cours ou Sujet d'examen.",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        doc_type = getattr(self, "type", None)
        if doc_type in {TypeDocument.MEMOIRE, TypeDocument.THESE} and not self.auteur:
            raise ValidationError({"auteur": "L'auteur est requis pour un memoire ou une these."})

        if doc_type in {TypeDocument.COURS, TypeDocument.EXAMEN} and not self.encadreur:
            raise ValidationError({"encadreur": "L'encadreur ou sujet est requis pour un cours ou un examen."})
