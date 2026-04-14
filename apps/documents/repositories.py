"""
apps/documents/repositories.py
"""
from django.db.models import Count, Q, QuerySet

from apps.documents.models import Document


class DocumentRepository:

    @staticmethod
    def _apply_allowed_level_names(
        queryset: QuerySet,
        allowed_level_names: list[str] | None = None,
    ) -> QuerySet:
        if allowed_level_names is None:
            return queryset
        if not allowed_level_names:
            return queryset.none()
        return queryset.filter(niveau__name__in=allowed_level_names)

    @staticmethod
    def get_all() -> QuerySet:
        return (
            Document.objects
            .select_related("filiere", "niveau", "specialite", "ue", "ajoute_par")
            .annotate(
                _nb_consultations=Count("consultations", distinct=True),
                _nb_favoris=Count("mis_en_favori_par", distinct=True),
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_by_id(
        document_id: str,
        *,
        allowed_level_names: list[str] | None = None,
    ) -> Document | None:
        queryset = DocumentRepository._apply_allowed_level_names(
            DocumentRepository.get_all(),
            allowed_level_names,
        )
        return queryset.filter(pk=document_id).first()

    @staticmethod
    def get_filtered(
        *,
        type_document: str | None = None,
        filiere_id: str | None = None,
        niveau_id: str | None = None,
        specialite_id: str | None = None,
        ue_id: str | None = None,
        ajoute_par_id: str | None = None,
        annee_academique_debut: str | None = None,
        search: str = "",
        allowed_level_names: list[str] | None = None,
    ) -> QuerySet:
        queryset = DocumentRepository._apply_allowed_level_names(
            DocumentRepository.get_all(),
            allowed_level_names,
        )

        if type_document:
            queryset = queryset.filter(type=type_document)
        if filiere_id:
            queryset = queryset.filter(filiere_id=filiere_id)
        if niveau_id:
            queryset = queryset.filter(niveau_id=niveau_id)
        if specialite_id:
            queryset = queryset.filter(specialite_id=specialite_id)
        if ue_id:
            queryset = queryset.filter(ue_id=ue_id)
        if ajoute_par_id:
            queryset = queryset.filter(ajoute_par_id=ajoute_par_id)
        if annee_academique_debut:
            queryset = queryset.filter(annee_academique_debut=annee_academique_debut)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(auteur__icontains=search)
                | Q(encadreur__icontains=search)
                | Q(description__icontains=search)
                | Q(specialite__name__icontains=search)
                | Q(ue__code__icontains=search)
                | Q(ue__name__icontains=search)
            )

        return queryset

    @staticmethod
    def create(**data) -> Document:
        return Document.objects.create(**data)

    @staticmethod
    def delete(document: Document) -> None:
        document.delete()
