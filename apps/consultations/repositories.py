"""
apps/consultations/repositories.py
"""
from django.db.models import Avg, Count, QuerySet, Sum

from apps.consultations.models import Consultation


class ConsultationRepository:

    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_all() -> QuerySet:
        return (
            Consultation.objects
            .select_related("user", "document")
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_id(consultation_id: str) -> Consultation | None:
        return (
            Consultation.objects
            .select_related("user", "document")
            .filter(pk=consultation_id)
            .first()
        )

    @staticmethod
    def get_by_user(user_id: str) -> QuerySet:
        return (
            Consultation.objects
            .select_related("user", "document")
            .filter(user_id=user_id)
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_document(document_id: str) -> QuerySet:
        return (
            Consultation.objects
            .select_related("user", "document")
            .filter(document_id=document_id)
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_type(type_consultation: str) -> QuerySet:
        return (
            Consultation.objects
            .select_related("user", "document")
            .filter(type_consultation=type_consultation)
            .order_by("-created_at")
        )

    @staticmethod
    def get_vues() -> QuerySet:
        return ConsultationRepository.get_by_type(
            Consultation.TypeConsultation.VUE
        )

    @staticmethod
    def get_recherches() -> QuerySet:
        return ConsultationRepository.get_by_type(
            Consultation.TypeConsultation.RECHERCHE
        )

    @staticmethod
    def get_en_cours(user_id: str) -> QuerySet:
        """Consultations démarrées mais pas encore terminées."""
        return (
            Consultation.objects
            .filter(
                user_id=user_id,
                type_consultation=Consultation.TypeConsultation.VUE,
                fin_consultation__isnull=True,
            )
            .order_by("-debut_consultation")
        )

    # ── Stats ─────────────────────────────────────────────────────────────────

    @staticmethod
    def stats_par_document(document_id: str) -> dict:
        return (
            Consultation.objects
            .filter(
                document_id=document_id,
                type_consultation=Consultation.TypeConsultation.VUE,
            )
            .aggregate(
                nb_vues=Count("id"),
                duree_moyenne=Avg("duree_secondes"),
                duree_totale=Sum("duree_secondes"),
            )
        )

    @staticmethod
    def top_documents(limit: int = 10) -> QuerySet:
        """Documents les plus consultés."""
        return (
            Consultation.objects
            .filter(
                type_consultation=Consultation.TypeConsultation.VUE,
                document__isnull=False,
            )
            .values("document_id", "document__title")
            .annotate(nb_vues=Count("id"))
            .order_by("-nb_vues")[:limit]
        )

    @staticmethod
    def top_recherches(limit: int = 10) -> QuerySet:
        """Termes de recherche les plus fréquents."""
        return (
            Consultation.objects
            .filter(type_consultation=Consultation.TypeConsultation.RECHERCHE)
            .values("recherche_query")
            .annotate(nb=Count("id"))
            .order_by("-nb")[:limit]
        )

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_vue(
        user_id: str | None,
        document_id: str,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        return Consultation.objects.create(
            user_id=user_id,
            document_id=document_id,
            type_consultation=Consultation.TypeConsultation.VUE,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def create_recherche(
        user_id: str | None,
        recherche_query: str,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> Consultation:
        return Consultation.objects.create(
            user_id=user_id,
            recherche_query=recherche_query,
            type_consultation=Consultation.TypeConsultation.RECHERCHE,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def terminer(consultation: Consultation) -> Consultation:
        consultation.terminer()
        return consultation

    @staticmethod
    def delete(consultation: Consultation) -> None:
        consultation.delete()