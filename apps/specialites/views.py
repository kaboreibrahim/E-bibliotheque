"""
apps/specialites/views.py
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

from apps.specialites.serializers import SpecialiteSerializer
from apps.specialites.services import SpecialiteService

_service = SpecialiteService()

SPECIALITE_LIST_EXAMPLE = OpenApiExample(
    "Réponse liste des spécialités",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "55555555-5555-5555-5555-555555555555",
            "name": "Droit des Affaires",
            "niveau_detail": {
                "id": "33333333-3333-3333-3333-333333333333",
                "name": "L1",
            },
            "est_doctorat": False,
            "nb_etudiants": 120,
            "nb_documents": 14,
            "nb_ues": 6,
            "created_at": "2026-04-03T11:00:00Z",
            "updated_at": "2026-04-03T11:00:00Z",
        }
    ],
)

SPECIALITE_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload création spécialité",
    request_only=True,
    value={
        "name": "Droit des Affaires",
        "niveau": "33333333-3333-3333-3333-333333333333",
    },
)

SPECIALITE_RESPONSE_EXAMPLE = OpenApiExample(
    "Réponse spécialité",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "55555555-5555-5555-5555-555555555555",
        "name": "Droit des Affaires",
        "niveau_detail": {
            "id": "33333333-3333-3333-3333-333333333333",
            "name": "L1",
        },
        "est_doctorat": False,
        "nb_etudiants": 120,
        "nb_documents": 14,
        "nb_ues": 6,
        "created_at": "2026-04-03T11:00:00Z",
        "updated_at": "2026-04-03T11:00:00Z",
    },
)

SPECIALITE_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID de la spécialité.",
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les spécialités",
        tags=["Spécialités"],
        parameters=[
            OpenApiParameter(name="niveau",  description="Filtrer par UUID de niveau", required=False, type=OpenApiTypes.UUID),
            OpenApiParameter(name="q",       description="Recherche par nom",          required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(response=SpecialiteSerializer(many=True), description="Liste des spécialités"),
        },
        examples=[SPECIALITE_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Créer une spécialité",
        tags=["Spécialités"],
        request=SpecialiteSerializer,
        responses={
            201: OpenApiResponse(response=SpecialiteSerializer, description="Spécialité créée"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[SPECIALITE_CREATE_REQUEST_EXAMPLE, SPECIALITE_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Détail d'une spécialité",
        tags=["Spécialités"],
        parameters=[SPECIALITE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=SpecialiteSerializer, description="Détail complet de la spécialité"),
            404: OpenApiResponse(description="Spécialité introuvable"),
        },
        examples=[SPECIALITE_RESPONSE_EXAMPLE],
    ),
    update=extend_schema(
        summary="Modifier une spécialité (PUT)",
        tags=["Spécialités"],
        parameters=[SPECIALITE_ID_PARAMETER],
        request=SpecialiteSerializer,
        responses={
            200: OpenApiResponse(response=SpecialiteSerializer, description="Spécialité mise à jour"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[SPECIALITE_CREATE_REQUEST_EXAMPLE, SPECIALITE_RESPONSE_EXAMPLE],
    ),
    partial_update=extend_schema(
        summary="Modifier une spécialité (PATCH)",
        tags=["Spécialités"],
        parameters=[SPECIALITE_ID_PARAMETER],
        request=SpecialiteSerializer,
        responses={
            200: OpenApiResponse(response=SpecialiteSerializer, description="Spécialité mise à jour partiellement"),
            400: OpenApiResponse(description="Données invalides"),
        },
        examples=[
            OpenApiExample("Payload patch spécialité", request_only=True, value={"name": "Droit Fiscal"}),
            SPECIALITE_RESPONSE_EXAMPLE,
        ],
    ),
    destroy=extend_schema(
        summary="Supprimer une spécialité (soft)",
        tags=["Spécialités"],
        parameters=[SPECIALITE_ID_PARAMETER],
        responses={204: OpenApiResponse(description="Spécialité supprimée")},
    ),
)
class SpecialiteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        niveau_id = request.query_params.get("niveau")
        q         = request.query_params.get("q", "").strip()
        qs = _service.list_specialites(niveau_id=niveau_id, q=q or None)
        return Response(SpecialiteSerializer(qs, many=True).data)

    def create(self, request):
        serializer = SpecialiteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            sp = _service.create_specialite(
                name=vd["name"],
                niveau_id=str(vd["niveau"]),
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SpecialiteSerializer(sp).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            sp = _service.get_specialite(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(SpecialiteSerializer(sp).data)

    def update(self, request, pk=None):
        serializer = SpecialiteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sp = _service.update_specialite(pk, name=serializer.validated_data["name"])
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SpecialiteSerializer(sp).data)

    def partial_update(self, request, pk=None):
        serializer = SpecialiteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data.get("name")
        if name:
            try:
                sp = _service.update_specialite(pk, name=name)
            except ValidationError as exc:
                return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                sp = _service.get_specialite(pk)
            except ValidationError as exc:
                return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(SpecialiteSerializer(sp).data)

    def destroy(self, request, pk=None):
        try:
            _service.delete_specialite(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
