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
from apps.documents.models import Document
from apps.users.models.etudiant_models import Etudiant


# =============================================================================
# ⭐  FAVORIS (Etudiant ↔ Document)
# =============================================================================
 
class Favori(SafeDeleteModel):
    """
    Un étudiant peut mettre un document en favori.
    Relation ManyToMany explicite pour pouvoir ajouter des métadonnées.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        related_name='favoris',
        verbose_name="Étudiant"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='mis_en_favori_par',
        verbose_name="Document"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté aux favoris le")
 
    class Meta:
        verbose_name        = "Favori"
        verbose_name_plural = "Favoris"
        unique_together     = ('etudiant', 'document')   # un seul favori par document/étudiant
        ordering            = ['-created_at']
 
    def __str__(self):
        return f"{self.etudiant.user.get_full_name()} ❤ {self.document.title}"
 