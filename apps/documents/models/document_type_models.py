import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TypeDocument(models.Model):
    EXAMEN = "EXAMEN"
    MEMOIRE = "MEMOIRE"
    THESE = "THESE"
    COURS = "COURS"
    AUTRE = "AUTRE"

    DEFAULT_TYPES = (
        (EXAMEN, "Examen"),
        (MEMOIRE, "Memoire"),
        (THESE, "These"),
        (COURS, "Cours"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, verbose_name="Code")
    name = models.CharField(max_length=100, unique=True, verbose_name="Libelle")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Type de document"
        verbose_name_plural = "Types de documents"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def normalize_code(cls, value: str | None) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()

    @classmethod
    def build_name_from_code(cls, code: str | None) -> str:
        normalized = cls.normalize_code(code)
        if not normalized:
            return ""
        labels = dict(cls.DEFAULT_TYPES)
        return labels.get(normalized, normalized.replace("_", " ").title())

    @classmethod
    def get_code(cls, value) -> str:
        if isinstance(value, cls):
            return cls.normalize_code(value.code)

        raw_code = getattr(value, "code", value)
        return cls.normalize_code(raw_code)

    @classmethod
    def get_display(cls, value) -> str:
        if isinstance(value, cls):
            return value.name

        return cls.build_name_from_code(cls.get_code(value))

    @classmethod
    def requires_auteur(cls, value) -> bool:
        return cls.get_code(value) in {cls.MEMOIRE, cls.THESE}

    @classmethod
    def requires_encadreur(cls, value) -> bool:
        return cls.get_code(value) in {cls.COURS, cls.EXAMEN}

    @property
    def nb_documents(self) -> int:
        return self.documents.count()

    def clean(self):
        super().clean()

        self.code = self.normalize_code(self.code)
        self.name = (self.name or "").strip()

        if not self.code:
            raise ValidationError({"code": "Le code du type de document est obligatoire."})

        if not self.name:
            self.name = self.build_name_from_code(self.code)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
