"""
apps/annee_academique/models.py
Annee universitaire (ex: 2025-2026) — une seule peut etre marquee "courante".
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel


class AnneeAcademique(SafeDeleteModel):
    """Annee academique dont les dates alimentent par defaut la validite des comptes etudiants."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_debut = models.DateField(verbose_name="Date de debut")
    date_fin = models.DateField(verbose_name="Date de fin")
    est_courante = models.BooleanField(
        default=False,
        verbose_name="Annee courante",
        help_text=(
            "Une seule annee academique peut etre marquee comme courante. "
            "Elle sert de valeur par defaut pour la validite des nouveaux comptes etudiants."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Annee academique"
        verbose_name_plural = "Annees academiques"
        ordering = ["-date_debut"]

    def __str__(self):
        return self.libelle

    @property
    def libelle(self) -> str:
        if not self.date_debut or not self.date_fin:
            return ""
        if self.date_debut.year == self.date_fin.year:
            return str(self.date_debut.year)
        return f"{self.date_debut.year}-{self.date_fin.year}"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError(
                {"date_fin": "La date de fin doit etre posterieure a la date de debut."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.est_courante:
                AnneeAcademique.objects.exclude(pk=self.pk).filter(
                    est_courante=True
                ).update(est_courante=False)

    @classmethod
    def get_courante(cls) -> "AnneeAcademique | None":
        return cls.objects.filter(est_courante=True).first()
