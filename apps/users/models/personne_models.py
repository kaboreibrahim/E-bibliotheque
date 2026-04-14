import uuid

from django.db import models
from safedelete.models import SOFT_DELETE_CASCADE, SafeDeleteModel

from apps.users.models.user_models import User


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Personne externe"
        verbose_name_plural = "Personnes externes"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"Personne externe : {self.user.get_full_name()}"
