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
# 🏫  FILIÈRE 
# =============================================================================
 
class Filiere(SafeDeleteModel):
    """Représente une filière universitaire (ex: Droit, Informatique)."""
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom de la filière",
        help_text="Ex : Droit, Informatique, Médecine"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name = "Filière"
        verbose_name_plural = "Filières"
        ordering = ['name']
 
    def __str__(self):
        return self.name
 
 