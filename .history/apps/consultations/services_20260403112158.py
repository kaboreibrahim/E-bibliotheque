"""
apps/favoris/services.py
Couche service – logique métier des favoris.
"""
from django.core.exceptions import ValidationError

from apps.favoris.models import Favori
from apps.favoris.repositories import FavoriRepository


class FavoriService:

    def __init__(self, repo: FavoriRepository | None = None):
        self.repo = repo or FavoriRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

    def list_favoris(
        self,
        etudiant_id: str | None = None,
        document_id: str | None = None,
    ):
        if etudiant_id:
            return self.repo.get_by_etudiant(etudiant_id)
        if document_id:
            return self.repo.get_by_document(document_id)
        return self.repo.get_all()

    def get_favori(self, favori_id: str) -> Favori:
        favori = self.repo.get_by_id(favori_id)
        if not favori:
            raise ValidationError(f"Favori introuvable : {favori_id}.")
        return favori

    def est_en_favori(self, etudiant_id: str, document_id: str) -> bool:
        """Vérifie si un document est déjà en favori pour un étudiant."""
        return self.repo.get_by_etudiant_and_document(etudiant_id, document_id) is not None

    # ── Commandes ─────────────────────────────────────────────────────────────

    def ajouter_favori(self, etudiant_id: str, document_id: str) -> Favori:
        """
        Ajoute un document aux favoris d'un étudiant.
        Lève une ValidationError si le favori existe déjà.
        """
        from apps.users.models.etudiant_models import Etudiant
        from apps.documents.models import Document

        if not Etudiant.objects.filter(pk=etudiant_id).exists():
            raise ValidationError(f"Étudiant introuvable : {etudiant_id}.")

        if not Document.objects.filter(pk=document_id).exists():
            raise ValidationError(f"Document introuvable : {document_id}.")

        if self.repo.get_by_etudiant_and_document(etudiant_id, document_id):
            raise ValidationError(
                "Ce document est déjà dans vos favoris."
            )

        return self.repo.create(etudiant_id=etudiant_id, document_id=document_id)

    def supprimer_favori(self, favori_id: str) -> None:
        favori = self.get_favori(favori_id)
        self.repo.delete(favori)

    def supprimer_favori_par_couple(self, etudiant_id: str, document_id: str) -> None:
        """Suppression directe sans connaître l'UUID du favori."""
        favori = self.repo.get_by_etudiant_and_document(etudiant_id, document_id)
        if not favori:
            raise ValidationError(
                "Ce document ne figure pas dans vos favoris."
            )
        self.repo.delete(favori)