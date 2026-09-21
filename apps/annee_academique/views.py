"""
apps/annee_academique/views.py
ViewSets DRF + annotations drf-spectacular (Swagger / ReDoc).
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.annee_academique.serializers import AnneeAcademiqueSerializer
from apps.annee_academique.services import AnneeAcademiqueService
from apps.users.permissions import IsAdministrateur

_service = AnneeAcademiqueService()

ANNEE_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID de l'année académique.",
)

ANNEE_RESPONSE_EXAMPLE = OpenApiExample(
    "Réponse année académique",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "55555555-5555-5555-5555-555555555555",
        "libelle": "2025-2026",
        "date_debut": "2025-10-01",
        "date_fin": "2026-07-31",
        "est_courante": True,
        "created_at": "2026-04-03T09:00:00Z",
        "updated_at": "2026-04-03T09:00:00Z",
    },
)

ANNEE_LIST_EXAMPLE = OpenApiExample(
    "Réponse liste des années académiques",
    response_only=True,
    status_codes=["200"],
    value=[ANNEE_RESPONSE_EXAMPLE.value],
)

ANNEE_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload création année académique",
    request_only=True,
    value={
        "date_debut": "2025-10-01",
        "date_fin": "2026-07-31",
        "est_courante": True,
    },
)

ANNEE_PATCH_REQUEST_EXAMPLE = OpenApiExample(
    "Payload changement d'année courante (PATCH)",
    request_only=True,
    value={"est_courante": True},
)

ANNEE_ERROR_EXAMPLE = OpenApiExample(
    "Erreur année académique introuvable",
    response_only=True,
    status_codes=["404"],
    value={"detail": "Année académique introuvable : 55555555-5555-5555-5555-555555555555."},
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les années académiques",
        tags=["Années académiques"],
        responses={
            200: OpenApiResponse(
                response=AnneeAcademiqueSerializer(many=True),
                description="Liste des années académiques.",
            ),
        },
        examples=[ANNEE_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Créer une année académique",
        tags=["Années académiques"],
        request=AnneeAcademiqueSerializer,
        description=(
            "Crée une nouvelle année académique. Si `est_courante` est à true, "
            "elle devient automatiquement l'année courante et toutes les autres "
            "repassent à false. Cette année sert alors de valeur par défaut pour "
            "la période de validité des nouveaux comptes étudiants. "
            "Réservé aux administrateurs."
        ),
        responses={
            201: OpenApiResponse(response=AnneeAcademiqueSerializer, description="Année académique créée."),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
        },
        examples=[ANNEE_CREATE_REQUEST_EXAMPLE, ANNEE_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Détail d'une année académique",
        tags=["Années académiques"],
        parameters=[ANNEE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=AnneeAcademiqueSerializer, description="Détail de l'année académique."),
            404: OpenApiResponse(description="Année académique introuvable."),
        },
        examples=[ANNEE_RESPONSE_EXAMPLE, ANNEE_ERROR_EXAMPLE],
    ),
    update=extend_schema(
        summary="Modifier une année académique (PUT)",
        tags=["Années académiques"],
        parameters=[ANNEE_ID_PARAMETER],
        request=AnneeAcademiqueSerializer,
        description="Réservé aux administrateurs.",
        responses={
            200: OpenApiResponse(response=AnneeAcademiqueSerializer, description="Année académique mise à jour."),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
            404: OpenApiResponse(description="Année académique introuvable."),
        },
        examples=[ANNEE_CREATE_REQUEST_EXAMPLE, ANNEE_RESPONSE_EXAMPLE],
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement une année académique (PATCH)",
        tags=["Années académiques"],
        parameters=[ANNEE_ID_PARAMETER],
        request=AnneeAcademiqueSerializer,
        description=(
            "Permet notamment de basculer l'année courante en envoyant "
            "uniquement `{\"est_courante\": true}`. Réservé aux administrateurs."
        ),
        responses={
            200: OpenApiResponse(response=AnneeAcademiqueSerializer, description="Année académique mise à jour."),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
            404: OpenApiResponse(description="Année académique introuvable."),
        },
        examples=[ANNEE_PATCH_REQUEST_EXAMPLE, ANNEE_RESPONSE_EXAMPLE],
    ),
    destroy=extend_schema(
        summary="Supprimer une année académique (soft delete)",
        tags=["Années académiques"],
        parameters=[ANNEE_ID_PARAMETER],
        description="Réservé aux administrateurs.",
        responses={
            204: OpenApiResponse(description="Année académique supprimée."),
            403: OpenApiResponse(description="Permission insuffisante."),
            404: OpenApiResponse(description="Année académique introuvable."),
        },
    ),
)
class AnneeAcademiqueViewSet(viewsets.ViewSet):
    """CRUD sur les années académiques. Écriture réservée aux administrateurs."""

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsAdministrateur()]
        return [IsAuthenticated()]

    def list(self, request):
        serializer = AnneeAcademiqueSerializer(_service.list_annees(), many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = AnneeAcademiqueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            annee = _service.create_annee(**serializer.validated_data)
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or {"detail": exc.messages}
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(AnneeAcademiqueSerializer(annee).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            annee = _service.get_annee(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(AnneeAcademiqueSerializer(annee).data)

    def update(self, request, pk=None):
        return self._update(request, pk, partial=False)

    def partial_update(self, request, pk=None):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            annee = _service.get_annee(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)

        serializer = AnneeAcademiqueSerializer(instance=annee, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            annee = _service.update_annee(pk, **serializer.validated_data)
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or {"detail": exc.messages}
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(AnneeAcademiqueSerializer(annee).data)

    def destroy(self, request, pk=None):
        try:
            _service.delete_annee(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Année académique courante",
        tags=["Années académiques"],
        description=(
            "Retourne l'année académique actuellement marquée comme courante — "
            "celle utilisée par défaut pour la validité des nouveaux comptes étudiants."
        ),
        responses={
            200: OpenApiResponse(response=AnneeAcademiqueSerializer, description="Année académique courante."),
            404: OpenApiResponse(description="Aucune année académique courante configurée."),
        },
        examples=[ANNEE_RESPONSE_EXAMPLE],
    )
    @action(detail=False, methods=["get"], url_path="courante")
    def courante(self, request):
        annee = _service.get_annee_courante()
        if not annee:
            return Response(
                {"detail": "Aucune année académique courante n'est configurée."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AnneeAcademiqueSerializer(annee).data)
