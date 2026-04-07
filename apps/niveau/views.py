"""
apps/niveau/views.py
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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.niveau.serializers import NiveauSerializer
from apps.niveau.services import NiveauService

_service = NiveauService()

NIVEAU_LIST_EXAMPLE = OpenApiExample(
    "Réponse liste des niveaux",
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

NIVEAU_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload création niveau",
    request_only=True,
    value={
        "filiere": "11111111-1111-1111-1111-111111111111",
        "name": "L1",
    },
)

NIVEAU_RESPONSE_EXAMPLE = OpenApiExample(
    "Réponse niveau",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "L1",
        "filiere_detail": {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Droit",
        },
        "created_at": "2026-04-03T10:00:00Z",
    },
)

NIVEAU_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID du niveau.",
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les niveaux",
        tags=["Niveaux"],
        parameters=[
            OpenApiParameter(
                name="filiere",
                description="Filtrer par UUID de filière",
                required=False,
                type=OpenApiTypes.UUID,
            )
        ],
        responses={
            200: OpenApiResponse(response=NiveauSerializer(many=True), description="Liste des niveaux"),
        },
        examples=[NIVEAU_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Créer un niveau",
        tags=["Niveaux"],
        request=NiveauSerializer,
        responses={
            201: OpenApiResponse(response=NiveauSerializer, description="Niveau créé"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[NIVEAU_CREATE_REQUEST_EXAMPLE, NIVEAU_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Détail d'un niveau",
        tags=["Niveaux"],
        parameters=[NIVEAU_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=NiveauSerializer, description="Détail complet du niveau"),
            404: OpenApiResponse(description="Niveau introuvable"),
        },
        examples=[NIVEAU_RESPONSE_EXAMPLE],
    ),
    destroy=extend_schema(
        summary="Supprimer un niveau (soft)",
        tags=["Niveaux"],
        parameters=[NIVEAU_ID_PARAMETER],
        responses={204: OpenApiResponse(description="Niveau supprimé")},
    ),
)
class NiveauViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        filiere_id = request.query_params.get("filiere")
        qs = _service.list_niveaux(filiere_id=filiere_id)
        return Response(NiveauSerializer(qs, many=True).data)

    def create(self, request):
        serializer = NiveauSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            niveau = _service.create_niveau(
                filiere_id=str(vd["filiere"]),
                name=vd["name"],
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(NiveauSerializer(niveau).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            niveau = _service.get_niveau(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(NiveauSerializer(niveau).data)

    def destroy(self, request, pk=None):
        try:
            _service.delete_niveau(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
