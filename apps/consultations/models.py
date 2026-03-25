import uuid
import logging
from datetime import datetime, timezone as dt_tz
 
from django.db import models
from django.utils import timezone
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
 
# Importer User et Document depuis leurs apps respectives
# from apps.users.models import User
# from apps.documents.models import Document
 
logger = logging.getLogger(__name__)


 
# =============================================================================
# 👁️  CONSULTATION  (PostgreSQL)
# =============================================================================
 
class Consultation(SafeDeleteModel):
    """
    Enregistre chaque interaction d'un utilisateur avec un document :
      - Vue d'un document (qui a vu quoi, quand)
      - Recherche effectuée
      - Durée de consultation
 
    Stocké dans PostgreSQL pour permettre des requêtes DRF (filtres, stats).
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    class TypeConsultation(models.TextChoices):
        VUE       = 'VUE',       'Vue du document'
        RECHERCHE = 'RECHERCHE', 'Recherche effectuée'
 
    # ── Identifiant ───────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
 
    # ── Qui ───────────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consultations',
        verbose_name="Utilisateur"
    )
 
    # ── Quoi ──────────────────────────────────────────────────────────────────
    type_consultation = models.CharField(
        max_length=20,
        choices=TypeConsultation.choices,
        verbose_name="Type de consultation"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consultations',
        verbose_name="Document consulté",
        help_text="Renseigné uniquement pour le type VUE."
    )
    recherche_query = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Terme recherché",
        help_text="Renseigné uniquement pour le type RECHERCHE."
    )
 
    # ── Durée ─────────────────────────────────────────────────────────────────
    debut_consultation = models.DateTimeField(
        default=timezone.now,
        verbose_name="Début de consultation"
    )
    fin_consultation = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fin de consultation"
    )
    duree_secondes = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Durée (secondes)",
        help_text="Calculée automatiquement si début et fin sont renseignés."
    )
 
    # ── Contexte technique ───────────────────────────────────────────────────
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="User-Agent (navigateur)"
    )
 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Enregistré le")
 
    class Meta:
        verbose_name        = "Consultation"
        verbose_name_plural = "Consultations"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['document', 'created_at']),
            models.Index(fields=['type_consultation']),
        ]
 
    def __str__(self):
        if self.type_consultation == self.TypeConsultation.VUE:
            return f"{self.user} a vu « {self.document} » ({self.created_at:%d/%m/%Y %H:%M})"
        return f"{self.user} a recherché « {self.recherche_query} » ({self.created_at:%d/%m/%Y %H:%M})"
 
    def save(self, *args, **kwargs):
        """Calcule automatiquement la durée si début et fin sont renseignés."""
        if self.debut_consultation and self.fin_consultation:
            delta = self.fin_consultation - self.debut_consultation
            self.duree_secondes = max(0, int(delta.total_seconds()))
        super().save(*args, **kwargs)
 
    # ── Helpers ───────────────────────────────────────────────────────────────
    def terminer(self):
        """Appeler cette méthode quand l'utilisateur quitte le document."""
        self.fin_consultation = timezone.now()
        self.save(update_fields=['fin_consultation', 'duree_secondes'])
 
    @property
    def duree_formatee(self):
        """Retourne la durée sous forme lisible ex: 2m 34s"""
        if not self.duree_secondes:
            return "—"
        m, s = divmod(self.duree_secondes, 60)
        return f"{m}m {s}s" if m else f"{s}s"