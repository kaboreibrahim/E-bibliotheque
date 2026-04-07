"""
apps/filiere/repositories.py
Pattern : Repository (Clean Architecture)
"""
from django.db.models import QuerySet
from apps.filiere.models import Filiere


class FiliereRepository:
    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_all() -> QuerySet:
        return Filiere.objects.all().order_by("name")

    @staticmethod
    def get_by_id(filiere_id: str) -> Filiere | None:
        return Filiere.objects.filter(pk=filiere_id).first()

    @staticmethod
    def get_by_name(name: str) -> Filiere | None:
        return Filiere.objects.filter(name__iexact=name).first()

    @staticmethod
    def search(q: str) -> QuerySet:
        return Filiere.objects.filter(name__icontains=q).order_by("name")

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create(name: str) -> Filiere:
        return Filiere.objects.create(name=name)

    @staticmethod
    def update(filiere: Filiere, **fields) -> Filiere:
        for attr, value in fields.items():
            setattr(filiere, attr, value)
        filiere.save(update_fields=list(fields.keys()) + ["updated_at"])
        return filiere

    @staticmethod
    def delete(filiere: Filiere) -> None:
        filiere.delete()  # soft-delete via SafeDelete