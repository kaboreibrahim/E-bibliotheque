from django.db import models


class TypeDocument(models.TextChoices):
    EXAMEN = "EXAMEN", "Examen"
    MEMOIRE = "MEMOIRE", "Memoire"
    THESE = "THESE", "These"
    COURS = "COURS", "Cours"
