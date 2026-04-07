"""
apps/favoris/services.py
Couche service - logique metier des favoris.
"""
from django.core.exceptions import ValidationError

from apps.favoris.models import Favori
from apps.favoris.repositories import FavoriRepository
from apps.history.models import HistoriqueActionService


class FavoriService:

    def __init__(self, repo: FavoriRepository | None = None):
        self.repo = repo or FavoriRepository()

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
        return self.repo.get_by_etudiant_and_document(etudiant_id, document_id) is not None

    def ajouter_favori(
        self,
        etudiant_id: str,
        document_id: str,
        acteur=None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Favori:
        from apps.documents.models import Document
        from apps.users.models.etudiant_models import Etudiant

        etudiant = Etudiant.objects.select_related("user").filter(pk=etudiant_id).first()
        if not etudiant:
            raise ValidationError(f"Etudiant introuvable : {etudiant_id}.")

        document = Document.objects.filter(pk=document_id).first()
        if not document:
            raise ValidationError(f"Document introuvable : {document_id}.")

        if self.repo.get_by_etudiant_and_document(etudiant_id, document_id):
            raise ValidationError("Ce document est deja dans vos favoris.")

        favori = self.repo.create(etudiant_id=etudiant_id, document_id=document_id)
        HistoriqueActionService.log_favori(
            "AJOUT",
            user=acteur or etudiant.user,
            favori=favori,
            etudiant=etudiant,
            document=document,
            ip=ip_address,
            ua=user_agent,
        )
        return favori

    def supprimer_favori(
        self,
        favori_id: str,
        acteur=None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> None:
        favori = self.get_favori(favori_id)
        HistoriqueActionService.log_favori(
            "SUPPRESSION",
            user=acteur or getattr(favori.etudiant, "user", None),
            favori=favori,
            ip=ip_address,
            ua=user_agent,
        )
        self.repo.delete(favori)

    def supprimer_favori_par_couple(
        self,
        etudiant_id: str,
        document_id: str,
        acteur=None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> None:
        favori = self.repo.get_by_etudiant_and_document(etudiant_id, document_id)
        if not favori:
            raise ValidationError("Ce document ne figure pas dans vos favoris.")

        HistoriqueActionService.log_favori(
            "SUPPRESSION",
            user=acteur or getattr(favori.etudiant, "user", None),
            favori=favori,
            ip=ip_address,
            ua=user_agent,
        )
        self.repo.delete(favori)
