"""
apps/consultations/services.py
Couche service - logique metier des consultations.
"""
from django.core.exceptions import ValidationError

from apps.consultations.models import Consultation
from apps.consultations.repositories import ConsultationRepository
from apps.history.models import HistoriqueActionService


class ConsultationService:

    def __init__(self, repo: ConsultationRepository | None = None):
        self.repo = repo or ConsultationRepository()

    def list_consultations(
        self,
        user_id: str | None = None,
        document_id: str | None = None,
        type_consultation: str | None = None,
    ):
        if user_id:
            return self.repo.get_by_user(user_id)
        if document_id:
            return self.repo.get_by_document(document_id)
        if type_consultation:
            valides = [c[0] for c in Consultation.TypeConsultation.choices]
            if type_consultation not in valides:
                raise ValidationError(
                    f"Type invalide. Valeurs autorisees : {', '.join(valides)}."
                )
            return self.repo.get_by_type(type_consultation)
        return self.repo.get_all()

    def get_consultation(self, consultation_id: str) -> Consultation:
        consultation = self.repo.get_by_id(consultation_id)
        if not consultation:
            raise ValidationError(f"Consultation introuvable : {consultation_id}.")
        return consultation

    def get_consultations_en_cours(self, user_id: str):
        return self.repo.get_en_cours(user_id)

    def stats_document(self, document_id: str) -> dict:
        return self.repo.stats_par_document(document_id)

    def top_documents(self, limit: int = 10):
        limit = min(max(1, limit), 50)
        return list(self.repo.top_documents(limit))

    def top_recherches(self, limit: int = 10):
        limit = min(max(1, limit), 50)
        return list(self.repo.top_recherches(limit))

    def enregistrer_vue(
        self,
        document_id: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        from apps.documents.models import Document

        document = Document.objects.filter(pk=document_id).first()
        if not document:
            raise ValidationError(f"Document introuvable : {document_id}.")

        consultation = self.repo.create_vue(
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        HistoriqueActionService.log_consultation(
            "VUE",
            user=getattr(consultation, "user", None),
            consultation=consultation,
            document=document,
            ip=ip_address,
            ua=user_agent,
        )
        return consultation

    def enregistrer_recherche(
        self,
        recherche_query: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        recherche_query = recherche_query.strip()
        if not recherche_query:
            raise ValidationError("Le terme de recherche ne peut pas etre vide.")
        if len(recherche_query) > 500:
            raise ValidationError("Le terme de recherche ne doit pas depasser 500 caracteres.")

        consultation = self.repo.create_recherche(
            user_id=user_id,
            recherche_query=recherche_query,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        HistoriqueActionService.log_consultation(
            "RECHERCHE",
            user=getattr(consultation, "user", None),
            consultation=consultation,
            recherche_query=recherche_query,
            ip=ip_address,
            ua=user_agent,
        )
        return consultation

    def terminer_consultation(self, consultation_id: str) -> Consultation:
        consultation = self.get_consultation(consultation_id)
        if consultation.type_consultation != Consultation.TypeConsultation.VUE:
            raise ValidationError(
                "Seules les consultations de type VUE peuvent etre terminees."
            )
        if consultation.fin_consultation:
            raise ValidationError("Cette consultation est deja terminee.")

        consultation = self.repo.terminer(consultation)
        HistoriqueActionService.log_consultation(
            "TERMINEE",
            user=consultation.user,
            consultation=consultation,
            document=consultation.document,
            ip=consultation.ip_address,
            ua=consultation.user_agent,
            details={"fin_consultation": consultation.fin_consultation.isoformat()},
        )
        return consultation

    def supprimer_consultation(self, consultation_id: str) -> None:
        consultation = self.get_consultation(consultation_id)
        self.repo.delete(consultation)
