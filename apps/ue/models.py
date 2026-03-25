"""
UE and ECUE models.
"""

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.niveau.models import Niveau


class UE(SafeDeleteModel):
    """Unite d'enseignement rattachee a un ou plusieurs niveaux."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, verbose_name="Code UE")
    name = models.CharField(max_length=200, verbose_name="Intitule")
    coef = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Coefficient",
        help_text="Coefficient total de l'UE, calcule a partir des ECUE.",
    )
    niveaux = models.ManyToManyField(
        Niveau,
        related_name="ues",
        blank=True,
        verbose_name="Niveaux concernes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unite d'Enseignement"
        verbose_name_plural = "Unites d'Enseignement"
        ordering = ["code"]

    @property
    def coef_total(self) -> Decimal:
        """Retourne la somme des coefficients des ECUE actifs."""
        if not self.pk:
            return self.coef or Decimal("0.00")

        total = self.ecues.aggregate(total=Sum("coef"))["total"]
        return total or Decimal("0.00")

    def sync_coef_from_ecues(self, save: bool = True) -> Decimal:
        """Met a jour le coefficient stocke avec la somme des ECUE."""
        total = self.coef_total
        self.coef = total

        if save and self.pk:
            type(self).objects.filter(pk=self.pk).update(coef=total)

        return total

    def __str__(self):
        return f"{self.code} - {self.name}"


class ECUE(SafeDeleteModel):
    """Element constitutif d'une UE."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ue = models.ForeignKey(
        UE,
        on_delete=models.CASCADE,
        related_name="ecues",
        verbose_name="UE",
    )
    code = models.CharField(max_length=20, verbose_name="Code ECUE")
    name = models.CharField(max_length=200, verbose_name="Intitule ECUE")
    coef = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Coefficient ECUE",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ECUE"
        verbose_name_plural = "ECUE"
        ordering = ["ue__code", "code"]
        unique_together = [("ue", "code")]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.ue.sync_coef_from_ecues()

    def delete(self, *args, **kwargs):
        ue = self.ue
        result = super().delete(*args, **kwargs)
        ue.sync_coef_from_ecues()
        return result

    def __str__(self):
        return f"{self.code} - {self.name}"
