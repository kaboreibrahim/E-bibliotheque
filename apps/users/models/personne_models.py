import uuid
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.users.models.user_models import User


def _combine_local_date(date_value, end_of_day=False):
    current_time = time.max if end_of_day else time.min
    combined = datetime.combine(date_value, current_time)
    return timezone.make_aware(combined, timezone.get_current_timezone())


class PersonneExterne(SafeDeleteModel):
    """Profil minimal d'une personne externe autorisee a consulter les documents."""

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profil_personne_externe",
        limit_choices_to={"user_type": User.UserType.PERSONNE_EXTERNE},
        verbose_name="Compte utilisateur",
    )
    numero_piece = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numero de piece",
    )
    profession = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Profession",
    )
    lieu_habitation = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Lieu d'habitation",
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
        verbose_name="Activation enregistree le",
        help_text="Date a laquelle la validite du compte a ete enregistree.",
    )
    compte_expire_le = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'expiration du compte",
        help_text="Calculee automatiquement a partir de la date de fin de validite.",
    )
    activation_suspendue = models.BooleanField(
        default=False,
        verbose_name="Activation suspendue",
        help_text=(
            "Empeche la reactivation automatique du compte jusqu'a une nouvelle "
            "activation manuelle."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Personne externe"
        verbose_name_plural = "Personnes externes"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"Personne externe : {self.user.get_full_name()}"

    @property
    def fenetre_validite_configuree(self) -> bool:
        return bool(self.date_debut_validite and self.date_fin_validite)

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
        else:
            self.compte_expire_le = None

        super().save(*args, **kwargs)
        self.synchroniser_activation()

    def est_dans_periode_validite(self, reference=None) -> bool:
        if not self.fenetre_validite_configuree:
            return self.user.is_active

        if self.activation_suspendue or not self.compte_active_le:
            return False

        reference = reference or timezone.now()
        return self.date_debut_validite_dt <= reference <= self.date_fin_validite_dt

    def synchroniser_activation(self, reference=None) -> bool:
        if not self.fenetre_validite_configuree:
            return False

        doit_etre_actif = self.est_dans_periode_validite(reference=reference)
        if self.user.is_active == doit_etre_actif:
            return False

        self.user.is_active = doit_etre_actif
        self.user.save(update_fields=["is_active", "updated_at"])
        return True

    @property
    def jours_restants(self) -> int | None:
        if not self.date_fin_validite:
            return None
        return (self.date_fin_validite - timezone.localdate()).days

    @property
    def est_expire(self) -> bool:
        if not self.compte_expire_le:
            return False
        return timezone.now() > self.compte_expire_le

    @property
    def statut_compte(self) -> str:
        if not self.fenetre_validite_configuree:
            return "Actif" if self.user.is_active else "Inactif"

        if not self.compte_active_le:
            debut = self.date_debut_validite.strftime("%d/%m/%Y")
            fin = self.date_fin_validite.strftime("%d/%m/%Y")
            return f"En attente d'activation ({debut} - {fin})"

        if self.est_expire:
            jours = abs(self.jours_restants or 0)
            return f"Expire depuis {jours} jour(s)"

        if self.activation_suspendue:
            return "Desactive manuellement"

        if timezone.now() < self.date_debut_validite_dt:
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

    def activer_compte(self):
        self.compte_active_le = timezone.now()
        self.activation_suspendue = False
        self.save()

    def desactiver_compte(self, manuel=True):
        if manuel and not self.activation_suspendue:
            self.activation_suspendue = True
            super().save(update_fields=["activation_suspendue", "updated_at"])

        if self.user.is_active:
            self.user.is_active = False
            self.user.save(update_fields=["is_active", "updated_at"])
