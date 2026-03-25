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
from apps.filiere.models import Filiere
# =============================================================================
# 🏫 NIVEAU
# =============================================================================



class Niveau(SafeDeleteModel):
    """Niveau d'études rattaché à une filière (L1, L2, L3, M1, M2, DOCTORAT)."""
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    class NiveauChoices(models.TextChoices):
        L1       = 'L1',       'Licence 1'
        L2       = 'L2',       'Licence 2'
        L3       = 'L3',       'Licence 3'
        M1       = 'M1',       'Master 1'
        M2       = 'M2',       'Master 2'
        DOCTORAT = 'DOCTORAT', 'Doctorat'
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   
    name = models.CharField(
        max_length=20,
        choices=NiveauChoices.choices,
        verbose_name="Niveau"
    )
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"
        unique_together = ( 'name')
        ordering = [ 'name']
 
    def __str__(self):
        return f" - {self.name}"