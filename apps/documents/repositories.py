"""
apps/documents/repositories.py
"""
from django.db.models import Count, Q, QuerySet, Sum

from apps.documents.models import Document, DocumentStorageConfiguration


class DocumentRepository:

    @staticmethod
    def _apply_student_scope(
        queryset: QuerySet,
        *,
        allowed_level_names: list[str] | None = None,
        allowed_filiere_id=None,
        allowed_specialite_name: str | None = None,
    ) -> QuerySet:
        if allowed_level_names is not None:
            if not allowed_level_names:
                return queryset.none()
            queryset = queryset.filter(niveau__name__in=allowed_level_names)

        if allowed_filiere_id:
            queryset = queryset.filter(filiere_id=allowed_filiere_id)

        if allowed_specialite_name:
            queryset = queryset.filter(
                Q(specialite__isnull=True)
                | Q(specialite__name__iexact=allowed_specialite_name)
            )

        return queryset

    @staticmethod
    def get_all() -> QuerySet:
        return (
            Document.objects
            .select_related("type", "filiere", "niveau", "specialite", "ue", "ajoute_par")
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
        allowed_filiere_id=None,
        allowed_specialite_name: str | None = None,
    ) -> Document | None:
        queryset = DocumentRepository._apply_student_scope(
            DocumentRepository.get_all(),
            allowed_level_names=allowed_level_names,
            allowed_filiere_id=allowed_filiere_id,
            allowed_specialite_name=allowed_specialite_name,
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
        allowed_filiere_id=None,
        allowed_specialite_name: str | None = None,
    ) -> QuerySet:
        queryset = DocumentRepository._apply_student_scope(
            DocumentRepository.get_all(),
            allowed_level_names=allowed_level_names,
            allowed_filiere_id=allowed_filiere_id,
            allowed_specialite_name=allowed_specialite_name,
        )

        if type_document:
            queryset = queryset.filter(type__code=type_document)
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
                | Q(description__icontains=search)
                | Q(specialite__name__icontains=search)
                | Q(ue__code__icontains=search)
                | Q(ue__name__icontains=search)
            )

        return queryset

    @staticmethod
    def get_storage_stats(
        *,
        allowed_level_names: list[str] | None = None,
        allowed_filiere_id=None,
        allowed_specialite_name: str | None = None,
    ) -> dict[str, int]:
        queryset = DocumentRepository._apply_student_scope(
            Document.objects.only("id", "file_size"),
            allowed_level_names=allowed_level_names,
            allowed_filiere_id=allowed_filiere_id,
            allowed_specialite_name=allowed_specialite_name,
        )

        # PERF-001 : agregation SQL (file_size est precalcule a chaque save())
        # au lieu d'un stat() disque par document dans une boucle Python.
        aggregates = queryset.aggregate(
            documents_count=Count("id"),
            documents_with_file_count=Count("id", filter=Q(file_size__isnull=False)),
            total_file_size=Sum("file_size"),
        )

        return {
            "documents_count": aggregates["documents_count"],
            "documents_with_file_count": aggregates["documents_with_file_count"],
            "total_file_size": aggregates["total_file_size"] or 0,
        }

    @staticmethod
    def get_storage_configuration() -> DocumentStorageConfiguration:
        return DocumentStorageConfiguration.get_solo()

    @staticmethod
    def create(**data) -> Document:
        return Document.objects.create(**data)

    @staticmethod
    def update(document: Document, **data) -> Document:
        for field, value in data.items():
            setattr(document, field, value)
        document.save()
        return document

    @staticmethod
    def delete(document: Document) -> None:
        document.delete()
