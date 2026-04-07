"""
apps/consultations/services.py
Couche service – logique métier des consultations.
"""
from django.core.exceptions import ValidationError

from apps.consultations.models import Consultation
from apps.consultations.repositories import ConsultationRepository


class ConsultationService:

    def __init__(self, repo: ConsultationRepository | None = None):
        self.repo = repo or ConsultationRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

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
                    f"Type invalide. Valeurs autorisées : {', '.join(valides)}."
                )
            return self.repo.get_by_type(type_consultation)
        return self.repo.get_all()

    def get_consultation(self, consultation_id: str) -> Consultation:
        c = self.repo.get_by_id(consultation_id)
        if not c:
            raise ValidationError(f"Consultation introuvable : {consultation_id}.")
        return c

    def get_consultations_en_cours(self, user_id: str):
        return self.repo.get_en_cours(user_id)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats_document(self, document_id: str) -> dict:
        return self.repo.stats_par_document(document_id)

    def top_documents(self, limit: int = 10):
        limit = min(max(1, limit), 50)
        return list(self.repo.top_documents(limit))

    def top_recherches(self, limit: int = 10):
        limit = min(max(1, limit), 50)
        return list(self.repo.top_recherches(limit))

    # ── Commandes ─────────────────────────────────────────────────────────────

    def enregistrer_vue(
        self,
        document_id: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        from apps.documents.models import Document
        if not Document.objects.filter(pk=document_id).exists():
            raise ValidationError(f"Document introuvable : {document_id}.")
        return self.repo.create_vue(
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def enregistrer_recherche(
        self,
        recherche_query: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        recherche_query = recherche_query.strip()
        if not recherche_query:
            raise ValidationError("Le terme de recherche ne peut pas être vide.")
        if len(recherche_query) > 500:
            raise ValidationError("Le terme de recherche ne doit pas dépasser 500 caractères.")
        return self.repo.create_recherche(
            user_id=user_id,
            recherche_query=recherche_query,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def terminer_consultation(self, consultation_id: str) -> Consultation:
        """
        Clôture une consultation VUE en renseignant fin_consultation
        et en calculant la durée automatiquement.
        """
        consultation = self.get_consultation(consultation_id)
        if consultation.type_consultation != Consultation.TypeConsultation.VUE:
            raise ValidationError(
                "Seules les consultations de type VUE peuvent être terminées."
            )
        if consultation.fin_consultation:
            raise ValidationError("Cette consultation est déjà terminée.")
        return self.repo.terminer(consultation)

    def supprimer_consultation(self, consultation_id: str) -> None:
        consultation = self.get_consultation(consultation_id)
        self.repo.delete(consultation)