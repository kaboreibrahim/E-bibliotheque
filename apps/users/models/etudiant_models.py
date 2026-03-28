"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — apps/etudiant/models.py
 Profil Étudiant avec système d'expiration de compte (1 mois glissant)
=============================================================================
"""

import random
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE


def generate_matricule():
    """Génère un matricule unique pour les étudiants : ETU-ANNÉE-XXXXX"""
    year = timezone.now().year
    return f"ETU{year}{random.randint(10000, 99999)}"


# =============================================================================
# 🎓  PROFIL ÉTUDIANT
# =============================================================================

class Etudiant(SafeDeleteModel):
    """
    Profil étendu d'un étudiant.

    Système d'expiration :
    ┌─────────────────────────────────────────────────────────┐
    │  Compte activé  →  expire après 30 jours                │
    │  Compte expiré  →  peut être réactivé (nouveau cycle)   │
    │  Réactivation   →  repart pour 30 jours depuis ce jour  │
    └─────────────────────────────────────────────────────────┘
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    DUREE_VALIDITE_JOURS = 30  # durée du cycle en jours

    # ── Identifiant ───────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Lien utilisateur ──────────────────────────────────────────────────────
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='profil_etudiant',
        limit_choices_to={'user_type': 'ETUDIANT'},
        verbose_name="Compte utilisateur"
    )

    matricule  = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
        verbose_name="Matricule étudiant",
        help_text="Généré automatiquement pour les étudiants."
    )

    # ── Scolarité ─────────────────────────────────────────────────────────────
    filiere = models.ForeignKey(
        'filiere.Filiere',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='etudiants',
        verbose_name="Filière"
    )
    niveau = models.ForeignKey(
        'niveau.Niveau',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='etudiants',
        verbose_name="Niveau"
    )
    specialite = models.ForeignKey(
        'specialites.Specialite',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='etudiants',
        verbose_name="Specialite",
        help_text="Renseigner pour M1, M2 et DOCTORAT. Laisser vide pour L1, L2 et L3."
    )
    annee_inscription = models.PositiveIntegerField(
        default=timezone.now().year,
        verbose_name="Année d'inscription"
    )

    # ── Système d'expiration ──────────────────────────────────────────────────
    compte_active_le = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Dernière activation du compte",
        help_text="Date de la dernière activation ou réactivation. "
                  "Le compte expire 30 jours après cette date."
    )
    compte_expire_le = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date d'expiration du compte",
        help_text="Calculée automatiquement : compte_active_le + 30 jours."
    )
    nb_reactivations = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de réactivations",
        help_text="Compteur historique de toutes les réactivations."
    )
    derniere_reactivation_par = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reactivations_effectuees',
        verbose_name="Dernière réactivation par",
        help_text="Admin ou Bibliothécaire ayant effectué la dernière réactivation."
    )

    # ── Dates standard ────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="Modifié le")

    class Meta:
        verbose_name        = "Étudiant"
        verbose_name_plural = "Étudiants"
        ordering            = ['user__last_name']

    def __str__(self):
        parcours = f"{self.filiere} - {self.niveau}"
        if self.specialite:
            parcours = f"{parcours} - {self.specialite.name}"
        return (
            f"{self.user.get_full_name()} | "
            f"{parcours} | "
            f"{self.statut_compte}"
        )

    # =========================================================================
    # 💾  SAVE — calcul automatique de la date d'expiration
    # =========================================================================

    def clean(self):
        super().clean()

        if self.specialite and self.niveau and self.specialite.niveau_id != self.niveau_id:
            raise ValidationError({
                'specialite': "La specialite doit appartenir au meme niveau que l'etudiant."
            })

        if self.specialite and self.niveau and self.niveau.name in {'L1', 'L2', 'L3'}:
            raise ValidationError({
                'specialite': "Le tronc commun (L1, L2, L3) ne doit pas avoir de specialite."
            })

    def save(self, *args, **kwargs):
        """
        À chaque activation/réactivation :
          - compte_expire_le = compte_active_le + 30 jours
        """
        self.full_clean()
        if self.compte_active_le:
            self.compte_expire_le = (
                self.compte_active_le
                + timedelta(days=self.DUREE_VALIDITE_JOURS)
            )

        if not self.matricule:
            self.matricule = self._generate_unique_matricule()

        super().save(*args, **kwargs)

  
 
    

    # =========================================================================
    # 📊  PROPRIÉTÉS — jours restants / statut
    # =========================================================================

    @property
    def jours_restants(self) -> int | None:
        """
        Nombre de jours restants avant expiration du compte.

        Retourne :
          - int positif  → compte actif, N jours restants
          - 0            → expire aujourd'hui
          - int négatif  → compte expiré depuis N jours
          - None         → compte jamais activé
        """
        if not self.compte_expire_le:
            return None
        delta = self.compte_expire_le - timezone.now()
        return delta.days

    @property
    def est_expire(self) -> bool:
        """Vrai si le compte a dépassé sa date d'expiration."""
        if not self.compte_expire_le:
            return False
        return timezone.now() > self.compte_expire_le

    @property
    def statut_compte(self) -> str:
        """Retourne un libellé lisible du statut du compte."""
        jours = self.jours_restants

        if jours is None:
            return "⚪ Jamais activé"
        if jours > 7:
            return f"✅ Actif ({jours} jours restants)"
        if 0 < jours <= 7:
            return f"⚠️ Expire bientôt ({jours} jours restants)"
        if jours == 0:
            return "🔴 Expire aujourd'hui"
        return f"❌ Expiré depuis {abs(jours)} jours"

    @property
    def pourcentage_validite(self) -> int | None:
        """
        Pourcentage de la durée de validité restante (0-100).
        Utile pour une barre de progression côté front.
        """
        jours = self.jours_restants
        if jours is None:
            return None
        pct = max(0, min(100, int((jours / self.DUREE_VALIDITE_JOURS) * 100)))
        return pct

    # =========================================================================
    # ⚡  ACTIONS — activation / réactivation / vérification
    # =========================================================================

    def activer_compte(self, effectue_par=None):
        """
        Active le compte pour la première fois.
        Lance le cycle de 30 jours à partir d'aujourd'hui.

        Args:
            effectue_par : instance User (admin/biblio) qui effectue l'activation.
        """
        self.compte_active_le         = timezone.now()
        self.derniere_reactivation_par = effectue_par
        # Active aussi le compte Django
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])
        self.save()

    def reactiver_compte(self, effectue_par=None):
        """
        Réactive un compte expiré.
        Repart pour un nouveau cycle de 30 jours depuis aujourd'hui.

        Args:
            effectue_par : instance User (admin/biblio) qui effectue la réactivation.
        """
        self.compte_active_le          = timezone.now()
        self.nb_reactivations         += 1
        self.derniere_reactivation_par = effectue_par
        # Réactive aussi le compte Django
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])
        self.save()

    def desactiver_compte(self):
        """
        Désactive manuellement le compte (soft).
        Désactive aussi le compte Django (is_active=False).
        """
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        # On ne touche pas compte_expire_le pour garder l'historique

    def verifier_et_desactiver_si_expire(self) -> bool:
        """
        Vérifie si le compte est expiré et le désactive automatiquement.
        À appeler dans une tâche Celery / cron quotidien.

        Retourne True si le compte vient d'être désactivé.
        """
        if self.est_expire and self.user.is_active:
            self.desactiver_compte()
            return True
        return False

    @classmethod
    def _generate_unique_matricule(cls):
        while True:
            matricule = generate_matricule()
            if not cls.objects.filter(matricule=matricule).exists():
                return matricule


# =============================================================================
# ⏰  TÂCHE CRON — à appeler quotidiennement (ex: Celery Beat)
# =============================================================================

def desactiver_comptes_expires():
    """
    Désactive tous les comptes étudiants dont la date d'expiration est dépassée.

    Appeler cette fonction chaque jour via Celery Beat ou un cron :

        # celery.py / tasks.py
        from apps.etudiant.models import desactiver_comptes_expires

        @app.task
        def tache_expiration_quotidienne():
            nb = desactiver_comptes_expires()
            return f"{nb} compte(s) désactivé(s)"

        # ou crontab Django (django-crontab) :
        # CRONJOBS = [('0 2 * * *', 'apps.etudiant.models.desactiver_comptes_expires')]
    """
    maintenant   = timezone.now()
    expires      = Etudiant.objects.filter(
        compte_expire_le__lt=maintenant,
        user__is_active=True
    ).select_related('user')

    nb_desactives = 0
    for etudiant in expires:
        etudiant.desactiver_compte()
        nb_desactives += 1

    return nb_desactives
