"""
Profil etudiant avec gestion de validite du compte.
"""

import random
import uuid
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.specialites.rules import (
    LIBELLE_NIVEAUX_AVEC_SPECIALITE,
    niveau_accepte_specialite,
    niveau_est_tronc_commun,
)


def generate_matricule():
    """Genere un matricule unique pour les etudiants : ETU + annee + 5 chiffres."""
    year = timezone.now().year
    return f"ETU{year}{random.randint(10000, 99999)}"


def _combine_local_date(date_value, end_of_day=False):
    """Convertit une date locale en datetime timezone-aware."""
    current_time = time.max if end_of_day else time.min
    combined = datetime.combine(date_value, current_time)
    return timezone.make_aware(combined, timezone.get_current_timezone())


class Etudiant(SafeDeleteModel):
    """Profil etendu d'un etudiant."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    DUREE_VALIDITE_JOURS = 30

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="profil_etudiant",
        limit_choices_to={"user_type": "ETUDIANT"},
        verbose_name="Compte utilisateur",
    )

    matricule = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Matricule etudiant",
        help_text="Genere automatiquement pour les etudiants.",
    )

    filiere = models.ForeignKey(
        "filiere.Filiere",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etudiants",
        verbose_name="Filiere",
    )
    niveau = models.ForeignKey(
        "niveau.Niveau",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etudiants",
        verbose_name="Niveau",
    )
    specialite = models.ForeignKey(
        "specialites.Specialite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etudiants",
        verbose_name="Specialite",
        help_text=f"Renseigner pour {LIBELLE_NIVEAUX_AVEC_SPECIALITE}.",
    )
    annee_inscription = models.PositiveIntegerField(
        default=timezone.now().year,
        verbose_name="Annee d'inscription",
    )

    date_debut_validite = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de debut de validite",
        help_text="Date a partir de laquelle le compte peut etre utilise.",
    )
    date_fin_validite = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin de validite",
        help_text="Date de fin de validite du compte.",
    )
    compte_active_le = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Derniere activation du compte",
        help_text=(
            "Date de la derniere activation ou reactivation. "
            "Si une periode de validite est fournie, elle pilote la date de fin."
        ),
    )
    compte_expire_le = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration du compte",
        help_text=(
            "Calculee automatiquement a partir de la date de fin de validite, "
            "ou de la duree par defaut si aucune periode n'est configuree."
        ),
    )
    activation_suspendue = models.BooleanField(
        default=False,
        verbose_name="Activation suspendue",
        help_text=(
            "Empêche la reactivation automatique du compte jusqu'a une nouvelle "
            "activation manuelle."
        ),
    )
    nb_reactivations = models.PositiveIntegerField(
        default=0,
        verbose_name="Nombre de reactivations",
        help_text="Compteur historique de toutes les reactivations.",
    )
    derniere_reactivation_par = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reactivations_effectuees",
        verbose_name="Derniere reactivation par",
        help_text="Admin ou bibliothecaire ayant effectue la derniere reactivation.",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Etudiant"
        verbose_name_plural = "Etudiants"
        ordering = ["user__last_name"]

    def __str__(self):
        parcours = f"{self.filiere} - {self.niveau}"
        if self.specialite:
            parcours = f"{parcours} - {self.specialite.name}"
        return f"{self.user.get_full_name()} | {parcours} | {self.statut_compte}"

    @property
    def fenetre_validite_configuree(self) -> bool:
        return bool(self.date_debut_validite and self.date_fin_validite)

    @property
    def gestion_validite_active(self) -> bool:
        return bool(
            self.fenetre_validite_configuree
            or self.compte_active_le
            or self.compte_expire_le
        )

    @property
    def date_debut_validite_dt(self):
        if not self.date_debut_validite:
            return None
        return _combine_local_date(self.date_debut_validite)

    @property
    def date_fin_validite_dt(self):
        if not self.date_fin_validite:
            return None
        return _combine_local_date(self.date_fin_validite, end_of_day=True)

    def clean(self):
        super().clean()

        if self.niveau and niveau_accepte_specialite(self.niveau.name) and not self.specialite:
            raise ValidationError(
                {"specialite": "Une specialite est requise pour ce niveau."}
            )

        if self.specialite and self.niveau and niveau_est_tronc_commun(self.niveau.name):
            raise ValidationError(
                {"specialite": "Ce niveau ne doit pas avoir de specialite."}
            )

        if self.specialite and self.niveau and self.specialite.niveau_id != self.niveau_id:
            raise ValidationError(
                {
                    "specialite": (
                        "La specialite doit appartenir au meme niveau que l'etudiant."
                    )
                }
            )

        if bool(self.date_debut_validite) != bool(self.date_fin_validite):
            raise ValidationError(
                {
                    "date_debut_validite": (
                        "Les dates de debut et de fin doivent etre renseignees ensemble."
                    ),
                    "date_fin_validite": (
                        "Les dates de debut et de fin doivent etre renseignees ensemble."
                    ),
                }
            )

        if (
            self.date_debut_validite
            and self.date_fin_validite
            and self.date_fin_validite < self.date_debut_validite
        ):
            raise ValidationError(
                {
                    "date_fin_validite": (
                        "La date de fin doit etre posterieure ou egale a la date de debut."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.fenetre_validite_configuree:
            self.compte_expire_le = self.date_fin_validite_dt
        elif self.compte_active_le:
            self.compte_expire_le = self.compte_active_le + timedelta(
                days=self.DUREE_VALIDITE_JOURS
            )
        else:
            self.compte_expire_le = None

        if not self.matricule:
            self.matricule = self._generate_unique_matricule()

        super().save(*args, **kwargs)
        self.synchroniser_activation()

    def est_dans_periode_validite(self, reference=None) -> bool:
        if not self.gestion_validite_active:
            return self.user.is_active

        if self.activation_suspendue or not self.compte_active_le:
            return False

        reference = reference or timezone.now()

        if self.fenetre_validite_configuree:
            return self.date_debut_validite_dt <= reference <= self.date_fin_validite_dt

        if not self.compte_expire_le:
            return False

        return reference <= self.compte_expire_le

    def synchroniser_activation(self, reference=None) -> bool:
        if not self.gestion_validite_active:
            return False

        doit_etre_actif = self.est_dans_periode_validite(reference=reference)
        if self.user.is_active == doit_etre_actif:
            return False

        self.user.is_active = doit_etre_actif
        self.user.save(update_fields=["is_active", "updated_at"])
        return True

    @property
    def jours_restants(self) -> int | None:
        if not self.compte_expire_le:
            return None

        if self.date_fin_validite:
            return (self.date_fin_validite - timezone.localdate()).days

        delta = self.compte_expire_le - timezone.now()
        return delta.days

    @property
    def est_expire(self) -> bool:
        if not self.compte_expire_le:
            return False
        return timezone.now() > self.compte_expire_le

    @property
    def statut_compte(self) -> str:
        if not self.gestion_validite_active:
            return "Actif" if self.user.is_active else "Jamais active"

        if not self.compte_active_le:
            if self.fenetre_validite_configuree:
                debut = self.date_debut_validite.strftime("%d/%m/%Y")
                fin = self.date_fin_validite.strftime("%d/%m/%Y")
                return f"En attente d'activation ({debut} - {fin})"
            return "Jamais active"

        if self.est_expire:
            jours = abs(self.jours_restants or 0)
            return f"Expire depuis {jours} jour(s)"

        if self.activation_suspendue:
            return "Desactive manuellement"

        if self.fenetre_validite_configuree and timezone.now() < self.date_debut_validite_dt:
            return f"Actif a partir du {self.date_debut_validite.strftime('%d/%m/%Y')}"

        jours = self.jours_restants
        if jours is None:
            return "Actif"
        if jours > 7:
            return f"Actif ({jours} jour(s) restants)"
        if 0 < jours <= 7:
            return f"Expire bientot ({jours} jour(s) restants)"
        if jours == 0:
            return "Expire aujourd'hui"
        return f"Expire depuis {abs(jours)} jour(s)"

    @property
    def pourcentage_validite(self) -> int | None:
        if not self.compte_expire_le or not self.compte_active_le:
            return None

        if self.fenetre_validite_configuree:
            duree_totale = max(
                (self.date_fin_validite - self.date_debut_validite).days + 1,
                1,
            )
        else:
            duree_totale = self.DUREE_VALIDITE_JOURS

        jours = self.jours_restants
        if jours is None:
            return None

        pct = max(0, min(100, int((jours / duree_totale) * 100)))
        return pct

    def activer_compte(self, effectue_par=None):
        self.compte_active_le = timezone.now()
        self.derniere_reactivation_par = effectue_par
        self.activation_suspendue = False
        self.save()

    def reactiver_compte(self, effectue_par=None):
        self.compte_active_le = timezone.now()
        self.nb_reactivations += 1
        self.derniere_reactivation_par = effectue_par
        self.activation_suspendue = False
        self.save()

    def desactiver_compte(self, manuel=True):
        if manuel and not self.activation_suspendue:
            self.activation_suspendue = True
            super().save(update_fields=["activation_suspendue", "updated_at"])

        if self.user.is_active:
            self.user.is_active = False
            self.user.save(update_fields=["is_active", "updated_at"])

    def verifier_et_desactiver_si_expire(self) -> bool:
        if self.est_expire and self.user.is_active:
            self.desactiver_compte(manuel=False)
            return True
        return False

    @classmethod
    def _generate_unique_matricule(cls):
        while True:
            matricule = generate_matricule()
            if not cls.objects.filter(matricule=matricule).exists():
                return matricule


def desactiver_comptes_expires():
    """Desactive tous les comptes etudiants dont la date de fin est depassee."""
    maintenant = timezone.now()
    expires = Etudiant.objects.filter(
        compte_expire_le__lt=maintenant,
        user__is_active=True,
    ).select_related("user")

    nb_desactives = 0
    for etudiant in expires:
        etudiant.desactiver_compte(manuel=False)
        nb_desactives += 1

    return nb_desactives
