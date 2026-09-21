"""
apps/annee_academique/repositories.py
"""
from django.db.models import QuerySet

from apps.annee_academique.models import AnneeAcademique


class AnneeAcademiqueRepository:
    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_all() -> QuerySet:
        return AnneeAcademique.objects.all().order_by("-date_debut")

    @staticmethod
    def get_by_id(annee_id: str) -> AnneeAcademique | None:
        return AnneeAcademique.objects.filter(pk=annee_id).first()

    @staticmethod
    def get_courante() -> AnneeAcademique | None:
        return AnneeAcademique.objects.filter(est_courante=True).first()

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create(**data) -> AnneeAcademique:
        return AnneeAcademique.objects.create(**data)

    @staticmethod
    def update(annee: AnneeAcademique, **fields) -> AnneeAcademique:
        for attr, value in fields.items():
            setattr(annee, attr, value)
        annee.save()
        return annee

    @staticmethod
    def delete(annee: AnneeAcademique) -> None:
        annee.delete()  # soft-delete via SafeDelete
