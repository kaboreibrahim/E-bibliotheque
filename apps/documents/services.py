"""
apps/documents/services.py
Couche service - logique metier des documents.
"""
from django.core.exceptions import ValidationError

from apps.consultations.models import Consultation
from apps.consultations.services import ConsultationService
from apps.documents.models import Document, TypeDocument
from apps.documents.repositories import DocumentRepository
from apps.history.models import HistoriqueActionService

DOCUMENT_LEVEL_ORDER = ("L1", "L2", "L3", "M1", "M2", "DOCTORAT")
DOCUMENT_LEVEL_RANKS = {
    level_name: rank for rank, level_name in enumerate(DOCUMENT_LEVEL_ORDER)
}


class DocumentService:

    def __init__(
        self,
        repo: DocumentRepository | None = None,
        consultation_service: ConsultationService | None = None,
    ):
        self.repo = repo or DocumentRepository()
        self.consultation_service = consultation_service or ConsultationService()

    @staticmethod
    def _get_allowed_level_names_for_user(user) -> list[str] | None:
        if not user or not getattr(user, "is_authenticated", False):
            return None

        if not getattr(user, "is_etudiant", False):
            return None

        try:
            profil_etudiant = user.profil_etudiant
        except AttributeError:
            return []

        niveau = getattr(profil_etudiant, "niveau", None)
        niveau_name = getattr(niveau, "name", None)
        if not niveau_name:
            return []

        max_rank = DOCUMENT_LEVEL_RANKS.get(niveau_name)
        if max_rank is None:
            return []

        return list(DOCUMENT_LEVEL_ORDER[: max_rank + 1])

    def list_documents(
        self,
        *,
        user=None,
        type_document: str | None = None,
        filiere_id: str | None = None,
        niveau_id: str | None = None,
        specialite_id: str | None = None,
        ue_id: str | None = None,
        ajoute_par_id: str | None = None,
        annee_academique_debut: str | None = None,
        search: str = "",
    ):
        if type_document:
            type_document = type_document.upper()
            valides = [c[0] for c in TypeDocument.choices]
            if type_document not in valides:
                raise ValidationError(
                    f"Type de document invalide. Valeurs autorisees : {', '.join(valides)}."
                )

        allowed_level_names = self._get_allowed_level_names_for_user(user)

        return self.repo.get_filtered(
            type_document=type_document,
            filiere_id=filiere_id,
            niveau_id=niveau_id,
            specialite_id=specialite_id,
            ue_id=ue_id,
            ajoute_par_id=ajoute_par_id,
            annee_academique_debut=annee_academique_debut,
            search=search.strip(),
            allowed_level_names=allowed_level_names,
        )

    def get_document(self, document_id: str, *, user=None) -> Document:
        document = self.repo.get_by_id(
            document_id,
            allowed_level_names=self._get_allowed_level_names_for_user(user),
        )
        if not document:
            raise ValidationError(f"Document introuvable : {document_id}.")
        return document

    def create_document(
        self,
        *,
        data: dict,
        ajoute_par,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Document:
        document = self.repo.create(**data, ajoute_par=ajoute_par)
        HistoriqueActionService.log_document(
            "AJOUT",
            user=ajoute_par,
            document=document,
            details={
                "filiere_id": str(document.filiere_id) if document.filiere_id else None,
                "niveau_id": str(document.niveau_id) if document.niveau_id else None,
                "specialite_id": str(document.specialite_id) if document.specialite_id else None,
                "ue_id": str(document.ue_id) if document.ue_id else None,
            },
            ip=ip_address,
            ua=user_agent,
        )
        return self.get_document(str(document.pk))

    def ouvrir_document(
        self,
        *,
        document_id: str,
        user=None,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> tuple[Document, Consultation]:
        document = self.get_document(document_id, user=user)
        consultation = self.consultation_service.enregistrer_vue(
            document_id=str(document.pk),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return document, consultation

    def supprimer_document(
        self,
        *,
        document_id: str,
        supprime_par,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> None:
        document = self.get_document(document_id)
        HistoriqueActionService.log_document(
            "SUPPRESSION",
            user=supprime_par,
            document=document,
            ip=ip_address,
            ua=user_agent,
        )
        self.repo.delete(document)
