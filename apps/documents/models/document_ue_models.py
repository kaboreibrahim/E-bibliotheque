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
        'specialites.Specialite',
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
        verbose_name="ECUE concernee",
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

        if self.specialite and self.niveau and self.specialite.niveau_id != self.niveau_id:
            raise ValidationError({"specialite": "La specialite doit appartenir au meme niveau que le document."})

        if self.specialite and self.niveau and self.niveau.name in {'L1', 'L2', 'L3'}:
            raise ValidationError({"specialite": "Le tronc commun (L1, L2, L3) ne doit pas avoir de specialite."})

        doc_type = getattr(self, "type", None)
        if doc_type in {TypeDocument.MEMOIRE, TypeDocument.THESE} and not self.auteur:
            raise ValidationError({"auteur": "L'auteur est requis pour un memoire ou une these."})

        if doc_type in {TypeDocument.COURS, TypeDocument.EXAMEN} and not self.encadreur:
            raise ValidationError({"encadreur": "L'encadreur ou sujet est requis pour un cours ou un examen."})
