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
 
 # =============================================================================
# ⚙️  UTILITAIRES
# =============================================================================
 
def user_avatar_upload_path(instance, filename):
    return f'users/avatars/{instance.id}_{filename}'
 
def document_file_upload_path(instance, filename):
    return f'documents/{instance.type}/{filename}'


# =============================================================================
# 👤  MANAGER UTILISATEUR PERSONNALISÉ
# =============================================================================
 
class UserManager(BaseUserManager):
    """
    Manager custom : connexion par email OU username pour Admin/Bibliothécaire.
    Les étudiants se connectent uniquement par matricule.
    """
 
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
 
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', User.UserType.ADMINISTRATEUR)
        return self.create_user(email, password, **extra_fields)



# =============================================================================
# 👤  UTILISATEUR (modèle central)
# =============================================================================
 
class User(AbstractUser, SafeDeleteModel):
    """
    Modèle utilisateur personnalisé.
 
    - ADMINISTRATEUR  → connexion email + mot de passe + Google Authenticator (TOTP)
    - BIBLIOTHECAIRE  → connexion email + mot de passe + Google Authenticator (TOTP)
    - ETUDIANT        → connexion matricule + mot de passe + Google Authenticator (TOTP)
 
    Tous les comptes supportent le 2FA (TOTP via Google Authenticator).
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    # -- Supprime le username par défaut --
    username = None
 
    class UserType(models.TextChoices):
        ETUDIANT        = 'ETUDIANT',        'Étudiant'
        BIBLIOTHECAIRE  = 'BIBLIOTHECAIRE',  'Bibliothécaire'
        ADMINISTRATEUR  = 'ADMINISTRATEUR',  'Administrateur'
 
    # ── Identifiants ──────────────────────────────────────────────────────────
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True, verbose_name="Adresse email")
  
    phone      = models.CharField(max_length=17, unique=True, verbose_name="Téléphone")
    user_type  = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.ETUDIANT,
        verbose_name="Type d'utilisateur"
    )
 
    # ── Profil ────────────────────────────────────────────────────────────────
    avatar        = models.ImageField(
        upload_to=user_avatar_upload_path,
        null=True, blank=True,
        verbose_name="Photo de profil"
    )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
 
    # ── Sécurité 2FA / Google Authenticator (TOTP) ───────────────────────────
    totp_secret      = models.CharField(
        max_length=64, null=True, blank=True,
        verbose_name="Secret TOTP (Google Authenticator)",
        help_text="Clé base32 générée lors de l'activation du 2FA."
    )
    is_2fa_enabled   = models.BooleanField(
        default=False,
        verbose_name="2FA activé",
        help_text="Obligatoire pour tous les types de comptes."
    )
    totp_verified_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Dernière vérification TOTP"
    )
 
    # ── Statut ────────────────────────────────────────────────────────────────
    is_active  = models.BooleanField(default=True, verbose_name="Compte actif")
    is_staff   = models.BooleanField(default=False)
 
    # ── Dates ─────────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="Modifié le")
 
    # ── Auth ──────────────────────────────────────────────────────────────────
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['phone', 'first_name', 'last_name']
 
    objects = UserManager()
 
    class Meta:
        verbose_name        = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering            = ['-created_at']
 
    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"
 
    # ── Sauvegarde ────────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        # Admin & Bibliothécaire doivent avoir is_staff=True
        if self.user_type in (self.UserType.ADMINISTRATEUR, self.UserType.BIBLIOTHECAIRE):
            self.is_staff = True
        super().save(*args, **kwargs)
 
    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def is_etudiant(self):
        return self.user_type == self.UserType.ETUDIANT
 
    @property
    def is_bibliothecaire(self):
        return self.user_type == self.UserType.BIBLIOTHECAIRE
 
    @property
    def is_admin(self):
        return self.user_type == self.UserType.ADMINISTRATEUR
 
    @property
    def requires_2fa(self):
        """Tous les comptes doivent obligatoirement utiliser le 2FA."""
        return self.user_type in (
            self.UserType.ETUDIANT,
            self.UserType.ADMINISTRATEUR,
            self.UserType.BIBLIOTHECAIRE
        )




# =============================================================================
# 🔑  SESSION / TOKEN DE REFRESH (optionnel – complète SimpleJWT)
# =============================================================================
 
class RefreshTokenBlacklist(SafeDeleteModel):
    """
    Liste noire des tokens JWT révoqués (déconnexion explicite).
    SimpleJWT gère déjà cela nativement — ce modèle est optionnel
    si vous souhaitez un contrôle plus fin (ex : déconnexion globale).
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='blacklisted_tokens',
        verbose_name="Utilisateur"
    )
    token_jti  = models.CharField(max_length=255, unique=True, verbose_name="JTI du token")
    revoked_at = models.DateTimeField(auto_now_add=True, verbose_name="Révoqué le")
 
    class Meta:
        verbose_name        = "Token révoqué"
        verbose_name_plural = "Tokens révoqués"
        ordering            = ['-revoked_at']
 
    def __str__(self):
        return f"Token révoqué – {self.user.email} ({self.revoked_at:%d/%m/%Y %H:%M})"
