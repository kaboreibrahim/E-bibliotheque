from django.core.exceptions import ValidationError
from django.db import models

from apps.documents.models.document_type_models import TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.ue.models import ECUE

class DocumentUE(models.Model):
    """
    Champs metier lies au schema Document_UE.

    - `auteur` est attendu surtout pour memoirs/theses.
    - `encadreur` est attendu surtout pour cours/examens.
    """

    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Filiere",
    )
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Niveau",
    )
        # ✅ SPECIALITE remplace NIVEAU
    specialite = models.ForeignKey(
        'specialite.Specialite',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name="Spécialité",
        help_text=(
            "Spécialité M1/M2/DOCTORAT du document. "
            "NULL pour les documents du tronc commun (L1/L2/L3) — "
            "dans ce cas le niveau est déduit via l'UE."
        )
    )
    ue = models.ForeignKey(
        ECUE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="UE concernee",
    )

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
