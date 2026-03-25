"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — apps/specialite/models.py

 RÈGLE MÉTIER :
 ┌─────────────────────────────────────────────────────────────────┐
 │  L1 / L2 / L3  → Tronc commun — PAS de spécialité             │
 │  M1 / M2       → Spécialité OBLIGATOIRE                        │
 │  DOCTORAT      → Spécialité OBLIGATOIRE                        │
 └─────────────────────────────────────────────────────────────────┘

 Relation :
   Niveau (M1/M2/DOCTORAT) ──(1,n)── Specialite
   Specialite ──(1,n)────────────── Etudiant
   Specialite ──(1,n)────────────── Document
=============================================================================
"""

import uuid
from django.core.exceptions import ValidationError
from django.db import models
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE


# Niveaux autorisant une spécialité
NIVEAUX_AVEC_SPECIALITE = ('M1', 'M2', 'DOCTORAT')
NIVEAUX_TRONC_COMMUN    = ('L1', 'L2', 'L3')


# =============================================================================
# 🎓  SPÉCIALITÉ
# =============================================================================

class Specialite(SafeDeleteModel):
    """
    Spécialité universitaire liée à un Niveau (M1, M2 ou DOCTORAT uniquement).

    Exemples :
      Niveau M1/M2  → Droit des Affaires
      Niveau M1/M2  → Droit politique de l'environnement et du développement durable
      Niveau M1/M2  → Master professionnel Droits de l'Homme, État de Droit et Bonne gouvernance
      Niveau DOCTORAT → Droit des Contentieux (thèse)

    Les niveaux L1, L2, L3 ne peuvent PAS avoir de spécialité (tronc commun).
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
        help_text="Uniquement M1, M2 ou DOCTORAT."
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
        Empêche d'associer une spécialité à un niveau L1, L2 ou L3.
        """
        if self.niveau and self.niveau.name in NIVEAUX_TRONC_COMMUN:
            raise ValidationError(
                f"Le niveau '{self.niveau.name}' est un tronc commun. "
                f"Les spécialités sont réservées aux niveaux : "
                f"{', '.join(NIVEAUX_AVEC_SPECIALITE)}."
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