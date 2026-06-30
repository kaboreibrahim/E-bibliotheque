"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — apps/specialite/models.py

 RÈGLE MÉTIER :
 ┌─────────────────────────────────────────────────────────────────┐
 │  L1 / L2 / L3  → Spécialité OBLIGATOIRE                        │
 │  M1 / M2 / DOC → Spécialité OBLIGATOIRE                        │
 └─────────────────────────────────────────────────────────────────┘

 Relation :
   Niveau (L1/L2/L3/M1/M2/DOCTORAT) ──(1,n)── Specialite
   Specialite ──(1,n)────────────── Etudiant
   Specialite ──(1,n)────────────── Document
=============================================================================
"""

import uuid
from django.core.exceptions import ValidationError
from django.db import models
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from apps.specialites.rules import (
    LIBELLE_NIVEAUX_AVEC_SPECIALITE,
    niveau_est_tronc_commun,
)


# =============================================================================
# 🎓  SPÉCIALITÉ
# =============================================================================

class Specialite(SafeDeleteModel):
    """
    Spécialité universitaire liée à un niveau autorisé.

    Exemples :
      Niveau L1/L2/L3/M1/M2  → Droit des Affaires
      Niveau L1/L2/L3/M1/M2  → Droit politique de l'environnement et du développement durable
      Niveau L1/L2/L3/M1/M2  → Master professionnel Droits de l'Homme, État de Droit et Bonne gouvernance
      Niveau DOCTORAT → Droit des Contentieux (thèse)
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=200,
        verbose_name="Nom de la spécialité"
    )

    # ── Lien niveau ───────────────────────────────────────────────────────────
    niveau = models.ForeignKey(
        'niveau.Niveau',
        on_delete=models.CASCADE,
        related_name='specialites',
        verbose_name="Niveau",
        help_text=f"Uniquement {LIBELLE_NIVEAUX_AVEC_SPECIALITE}."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Spécialité"
        verbose_name_plural = "Spécialités"
        ordering            = ['niveau__name', 'name']
        unique_together     = ('name', 'niveau')  # même nom ne peut pas exister deux fois dans le même niveau

    def __str__(self):
        return f"{self.name} ({self.niveau.name})"

    # ── Validation métier ─────────────────────────────────────────────────────

    def clean(self):
        """
        Empêche d'associer une spécialité à un niveau non autorisé.
        """
        if self.niveau and niveau_est_tronc_commun(self.niveau.name):
            raise ValidationError(
                f"Le niveau '{self.niveau.name}' n'accepte pas de specialite. "
                f"Les specialites sont reservees aux niveaux : {LIBELLE_NIVEAUX_AVEC_SPECIALITE}."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def est_doctorat(self):
        return self.niveau.name == 'DOCTORAT'

    @property
    def nb_etudiants(self):
        return self.etudiants.count()

    @property
    def nb_documents(self):
        return self.documents.count()

    @property
    def nb_ues(self):
        return self.ues.count()
