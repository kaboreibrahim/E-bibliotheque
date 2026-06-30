"""
apps/favoris/repositories.py
"""
from django.db.models import QuerySet
from apps.favoris.models import Favori


class FavoriRepository:

    @staticmethod
    def get_all() -> QuerySet:
        return Favori.objects.select_related(
            "etudiant__user", "document"
        ).all()

    @staticmethod
    def get_by_id(favori_id: str) -> Favori | None:
        return (
            Favori.objects
            .select_related("etudiant__user", "document")
            .filter(pk=favori_id)
            .first()
        )

    @staticmethod
    def get_by_etudiant(etudiant_id: str) -> QuerySet:
        return (
            Favori.objects
            .select_related("etudiant__user", "document")
            .filter(etudiant_id=etudiant_id)
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_document(document_id: str) -> QuerySet:
        return (
            Favori.objects
            .select_related("etudiant__user", "document")
            .filter(document_id=document_id)
        )

    @staticmethod
    def get_by_etudiant_and_document(etudiant_id: str, document_id: str) -> Favori | None:
        return Favori.objects.filter(
            etudiant_id=etudiant_id,
            document_id=document_id,
        ).first()

    @staticmethod
    def create(etudiant_id: str, document_id: str) -> Favori:
        return Favori.objects.create(
            etudiant_id=etudiant_id,
            document_id=document_id,
        )

    @staticmethod
    def delete(favori: Favori) -> None:
        favori.delete()  # soft-delete via SafeDelete