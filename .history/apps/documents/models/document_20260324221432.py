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
 
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, User
from django.db import models
from django.utils import timezone
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.ue.models import UE
from apps.users.models.user_models import document_file_upload_path
document_file_upload_path
# =============================================================================
# 📄  DOCUMENTS
# ============================================================================= 
 
class Document(SafeDeleteModel):
    """
    Document de la bibliothèque (Examen, Mémoire, Thèse, Cours…).
    Associé à une ou plusieurs UE, filières et niveaux.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    class TypeDocument(models.TextChoices):
        EXAMEN   = 'EXAMEN',   'Examen'
        MEMOIRE  = 'MEMOIRE',  'Mémoire'
        THESE    = 'THESE',    'Thèse'
        COURS    = 'COURS',    'Cours'
 
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=255, verbose_name="Titre")
    type        = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
        verbose_name="Type de document"
    )
    file_path   = models.FileField(
        upload_to=document_file_upload_path,
        verbose_name="Fichier"
    )
    description = models.TextField(blank=True, verbose_name="Description")
 
    # ── Relations ─────────────────────────────────────────────────────────────
    filiere  = models.ForeignKey(
        Filiere,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name="Filière"
    )
    niveau   = models.ForeignKey(
        Niveau,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name="Niveau"
    )
    ue       = models.ForeignKey(
        UE,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name="UE concernée"
    )
 
    # ── Auteur / Encadreur (selon le type) ───────────────────────────────────
    auteur    = models.CharField(
        max_length=200, blank=True,
        verbose_name="Auteur",
        help_text="Pour Mémoire et Thèse."
    )
    encadreur = models.CharField(
        max_length=200, blank=True,
        verbose_name="Encadreur / Sujet",
        help_text="Pour Cours ou Sujet d'examen."
    )
 
    # ── Ajouté par ────────────────────────────────────────────────────────────
    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents_ajoutes',
        verbose_name="Ajouté par"
    )
 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté le")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="Modifié le")
 
    class Meta:
        verbose_name        = "Document"
        verbose_name_plural = "Documents"
        ordering            = ['-created_at']
 
    def __str__(self):
        return f"[{self.type}] {self.title}"
