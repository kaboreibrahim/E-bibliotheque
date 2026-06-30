"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE - models.py
 Stack : Django + DRF + SimpleJWT + django-safedelete + django-otp (TOTP)
=============================================================================
"""
 
import uuid
import random
import string
from datetime import timedelta
 
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from apps.users.models.user_models import User


# =============================================================================
# 📖  PROFIL BIBLIOTHÉCAIRE
# =============================================================================
 
class Bibliothecaire(SafeDeleteModel):
    """
    Profil étendu d'un bibliothécaire.
    Peut gérer les documents et les utilisateurs.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil_bibliothecaire',
        limit_choices_to={'user_type': User.UserType.BIBLIOTHECAIRE},
        verbose_name="Compte utilisateur"
    )
    # Permissions spécifiques
    peut_gerer_documents    = models.BooleanField(default=True,  verbose_name="Gérer les documents")
    peut_gerer_utilisateurs = models.BooleanField(default=False, verbose_name="Gérer les utilisateurs")
 
    badge_number = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
        verbose_name="Numéro de badge"
    )
    date_prise_poste = models.DateField(null=True, blank=True, verbose_name="Date de prise de poste")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name        = "Bibliothécaire"
        verbose_name_plural = "Bibliothécaires"
        ordering            = ['user__last_name']
 
    def __str__(self):
        return f"Bibliothécaire : {self.user.get_full_name()}"
 