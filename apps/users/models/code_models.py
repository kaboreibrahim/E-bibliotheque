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
# 🔐  CODE DE VÉRIFICATION (OTP email + activation + reset password)
# =============================================================================
 
class CodeVerification(SafeDeleteModel):
    """
    Code OTP à 6 chiffres envoyé par email.
 
    Types supportés :
    - activation       → activation du compte
    - password_reset   → réinitialisation du mot de passe
    - email_change     → changement d'email
    - code_OTP         → second facteur pour les étudiants (2FA email)
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    TYPE_CHOICES = [
        ('activation',     'Activation de compte'),
        ('password_reset', 'Réinitialisation mot de passe'),
        ('email_change',   "Changement d'email"),
        ('code_OTP',       'Code OTP (2FA email)'),
    ]
 
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user     = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='codes_verification',
        verbose_name="Utilisateur"
    )
    code      = models.CharField(max_length=6,  verbose_name="Code")
    type_code = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type de code")
    email     = models.EmailField(verbose_name="Email de destination")
 
    is_used      = models.BooleanField(default=False,    verbose_name="Utilisé")
    attempts     = models.PositiveIntegerField(default=0, verbose_name="Tentatives")
    max_attempts = models.PositiveIntegerField(default=3, verbose_name="Max tentatives")
 
    expires_at = models.DateTimeField(verbose_name="Expire à")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    used_at    = models.DateTimeField(null=True, blank=True, verbose_name="Utilisé le")
 
    class Meta:
        verbose_name        = "Code de vérification"
        verbose_name_plural = "Codes de vérification"
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'type_code', 'is_used']),
            models.Index(fields=['code', 'email']),
        ]
 
    def __str__(self):
        return f"{self.user.email} – {self.code} ({self.get_type_code_display()})"
 
    # ── Méthodes de classe ────────────────────────────────────────────────────
 
    @classmethod
    def generate_code(cls):
        """Génère un code numérique à 6 chiffres."""
        return ''.join(random.choices(string.digits, k=6))
 
    @classmethod
    def create_verification_code(cls, user, type_code, email=None, validity_seconds=180):
        """
        Crée un nouveau code OTP.
        Invalide automatiquement les anciens codes du même type.
        """
        # Invalider les anciens codes non utilisés
        cls.objects.filter(user=user, type_code=type_code, is_used=False).update(is_used=True)
 
        code       = cls.generate_code()
        expires_at = timezone.now() + timedelta(seconds=validity_seconds)
 
        return cls.objects.create(
            user=user,
            code=code,
            type_code=type_code,
            email=email or user.email,
            expires_at=expires_at
        )
 
    # ── Méthodes d'instance ───────────────────────────────────────────────────
 
    def is_expired(self):
        """Vrai si le code a dépassé sa durée de validité."""
        return timezone.now() > self.expires_at
 
    def is_valid(self):
        """Vrai si le code est encore utilisable."""
        return (
            not self.is_used
            and not self.is_expired()
            and self.attempts < self.max_attempts
        )
 
    def mark_as_used(self):
        """Marque le code comme consommé."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
 
    def increment_attempts(self):
        """
        Incrémente le compteur de tentatives.
        Retourne True si le nombre maximum est atteint.
        """
        self.attempts += 1
        self.save(update_fields=['attempts'])
        return self.attempts >= self.max_attempts