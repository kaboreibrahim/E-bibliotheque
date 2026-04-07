from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models

from apps.documents.models.document_type_models import TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.rules import (
    LIBELLE_NIVEAUX_AVEC_SPECIALITE,
    niveau_accepte_specialite,
    niveau_est_tronc_commun,
)
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
            f"Spécialité {LIBELLE_NIVEAUX_AVEC_SPECIALITE} du document."
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
    annee_academique_debut = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        validators=[MinValueValidator(1900), MaxValueValidator(9998)],
        verbose_name="Annee academique (debut)",
        help_text=(
            "Saisir l'annee de debut. Ex: 2024 pour 2024-2025. "
            "Les archives anciennes comme 1960-1961 sont aussi supportees."
        ),
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

    @property
    def annee_academique(self):
        if self.annee_academique_debut is None:
            return None
        return f"{self.annee_academique_debut}-{self.annee_academique_debut + 1}"

    def clean(self):
        super().clean()

        if self._state.adding and self.annee_academique_debut is None:
            raise ValidationError(
                {"annee_academique_debut": "L'annee academique est obligatoire lors de l'ajout d'un document."}
            )

        if self.niveau and niveau_accepte_specialite(self.niveau.name) and not self.specialite:
            raise ValidationError({"specialite": "Une specialite est requise pour ce niveau."})

        if self.specialite and self.niveau and niveau_est_tronc_commun(self.niveau.name):
            raise ValidationError({"specialite": "Ce niveau ne doit pas avoir de specialite."})

        if self.specialite and self.niveau and self.specialite.niveau_id != self.niveau_id:
            raise ValidationError({"specialite": "La specialite doit appartenir au meme niveau que le document."})

        doc_type = getattr(self, "type", None)
        if doc_type in {TypeDocument.MEMOIRE, TypeDocument.THESE} and not self.auteur:
            raise ValidationError({"auteur": "L'auteur est requis pour un memoire ou une these."})

        if doc_type in {TypeDocument.COURS, TypeDocument.EXAMEN} and not self.encadreur:
            raise ValidationError({"encadreur": "L'encadreur ou sujet est requis pour un cours ou un examen."})
