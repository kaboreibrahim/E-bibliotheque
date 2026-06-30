"""
apps/niveau/repositories.py
"""
from django.db.models import QuerySet
from apps.niveau.models import Niveau


class NiveauRepository:

    @staticmethod
    def get_all() -> QuerySet:
        return Niveau.objects.select_related("filiere").all()

    @staticmethod
    def get_by_id(niveau_id: str) -> Niveau | None:
        return Niveau.objects.select_related("filiere").filter(pk=niveau_id).first()

    @staticmethod
    def get_by_filiere(filiere_id: str) -> QuerySet:
        return Niveau.objects.select_related("filiere").filter(filiere_id=filiere_id)

    @staticmethod
    def get_by_filiere_and_name(filiere_id: str, name: str) -> Niveau | None:
        return Niveau.objects.filter(filiere_id=filiere_id, name=name).first()

    @staticmethod
    def create(filiere_id: str, name: str) -> Niveau:
        return Niveau.objects.create(filiere_id=filiere_id, name=name)

    @staticmethod
    def delete(niveau: Niveau) -> None:
        niveau.delete()