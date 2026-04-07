"""
apps/filiere/views.py
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

from apps.filiere.serializers import FiliereMinimalSerializer, FiliereSerializer
from apps.niveau.serializers import NiveauSerializer
from apps.filiere.services import FiliereService

_service = FiliereService()

FILIERE_LIST_EXAMPLE = OpenApiExample(
    "Réponse liste des filières",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Droit",
            "created_at": "2026-04-03T09:00:00Z",
            "updated_at": "2026-04-03T09:00:00Z",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Informatique",
            "created_at": "2026-04-03T09:05:00Z",
            "updated_at": "2026-04-03T09:05:00Z",
        },
    ],
)

FILIERE_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload création filière",
    request_only=True,
    value={"name": "Droit"},
)

FILIERE_RESPONSE_EXAMPLE = OpenApiExample(
    "Réponse filière",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Droit",
        "created_at": "2026-04-03T09:00:00Z",
        "updated_at": "2026-04-03T09:00:00Z",
    },
)

FILIERE_NIVEAUX_RESPONSE_EXAMPLE = OpenApiExample(
    "Réponse niveaux d'une filière",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "name": "L1",
            "filiere_detail": {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "Droit",
            },
            "created_at": "2026-04-03T10:00:00Z",
        },
        {
            "id": "44444444-4444-4444-4444-444444444444",
            "name": "M1",
            "filiere_detail": {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "Droit",
            },
            "created_at": "2026-04-03T10:05:00Z",
        },
    ],
)

FILIERE_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID de la filière.",
)


# ─────────────────────────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(
        summary="Lister les filières",
        tags=["Filières"],
        parameters=[
            OpenApiParameter(name="q", description="Recherche par nom", required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(response=FiliereSerializer(many=True), description="Liste des filières"),
        },
        examples=[FILIERE_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Créer une filière",
        tags=["Filières"],
        request=FiliereSerializer,
        responses={
            201: OpenApiResponse(response=FiliereSerializer, description="Filière créée"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[FILIERE_CREATE_REQUEST_EXAMPLE, FILIERE_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Détail d'une filière",
        tags=["Filières"],
        parameters=[FILIERE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=FiliereSerializer, description="Détail complet de la filière"),
            404: OpenApiResponse(description="Filière introuvable"),
        },
        examples=[FILIERE_RESPONSE_EXAMPLE],
    ),
    update=extend_schema(
        summary="Modifier une filière (PUT)",
        tags=["Filières"],
        parameters=[FILIERE_ID_PARAMETER],
        request=FiliereSerializer,
        responses={
            200: OpenApiResponse(response=FiliereSerializer, description="Filière mise à jour"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[FILIERE_CREATE_REQUEST_EXAMPLE, FILIERE_RESPONSE_EXAMPLE],
    ),
    partial_update=extend_schema(
        summary="Modifier une filière (PATCH)",
        tags=["Filières"],
        parameters=[FILIERE_ID_PARAMETER],
        request=FiliereSerializer,
        responses={
            200: OpenApiResponse(response=FiliereSerializer, description="Filière mise à jour partiellement"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[
            OpenApiExample("Payload patch filière", request_only=True, value={"name": "Droit Privé"}),
            FILIERE_RESPONSE_EXAMPLE,
        ],
    ),
    destroy=extend_schema(
        summary="Supprimer une filière (soft)",
        tags=["Filières"],
        parameters=[FILIERE_ID_PARAMETER],
        responses={204: OpenApiResponse(description="Filière supprimée")},
    ),
)
class FiliereViewSet(viewsets.ViewSet):
    """
    CRUD complet sur les filières universitaires.
    """
    permission_classes = [IsAuthenticated]

    # ── GET /filieres/ ────────────────────────────────────────────────────────
    def list(self, request):
        q = request.query_params.get("q", "").strip()
        qs = _service.search_filieres(q) if q else _service.list_filieres()
        serializer = FiliereSerializer(qs, many=True)
        return Response(serializer.data)

    # ── POST /filieres/ ───────────────────────────────────────────────────────
    def create(self, request):
        serializer = FiliereSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            filiere = _service.create_filiere(**serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FiliereSerializer(filiere).data, status=status.HTTP_201_CREATED)

    # ── GET /filieres/{id}/ ───────────────────────────────────────────────────
    def retrieve(self, request, pk=None):
        try:
            filiere = _service.get_filiere(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(FiliereSerializer(filiere).data)

    # ── PUT /filieres/{id}/ ───────────────────────────────────────────────────
    def update(self, request, pk=None):
        serializer = FiliereSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            filiere = _service.update_filiere(pk, **serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FiliereSerializer(filiere).data)

    # ── PATCH /filieres/{id}/ ─────────────────────────────────────────────────
    def partial_update(self, request, pk=None):
        serializer = FiliereSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            filiere = _service.update_filiere(pk, **serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FiliereSerializer(filiere).data)

    # ── DELETE /filieres/{id}/ ────────────────────────────────────────────────
    def destroy(self, request, pk=None):
        try:
            _service.delete_filiere(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── GET /filieres/{id}/niveaux/ ───────────────────────────────────────────
    @extend_schema(
        summary="Niveaux d'une filière",
        tags=["Filières"],
        parameters=[FILIERE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=NiveauSerializer(many=True), description="Liste des niveaux de la filière"),
            404: OpenApiResponse(description="Filière introuvable"),
        },
        examples=[FILIERE_NIVEAUX_RESPONSE_EXAMPLE],
    )
    @action(detail=True, methods=["get"], url_path="niveaux")
    def niveaux(self, request, pk=None):
        try:
            filiere = _service.get_filiere(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        serializer = NiveauSerializer(filiere.niveaux.all(), many=True)
        return Response(serializer.data)
