"""
apps/specialites/views.py
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.specialites.serializers import SpecialiteSerializer
from apps.specialites.services import SpecialiteService

_service = SpecialiteService()


@extend_schema_view(
    list=extend_schema(
        summary="Lister les spécialités",
        tags=["Spécialités"],
        parameters=[
            OpenApiParameter(name="niveau",  description="Filtrer par UUID de niveau", required=False, type=str),
            OpenApiParameter(name="q",       description="Recherche par nom",          required=False, type=str),
        ],
    ),
    create=extend_schema(summary="Créer une spécialité",               tags=["Spécialités"]),
    retrieve=extend_schema(summary="Détail d'une spécialité",          tags=["Spécialités"]),
    update=extend_schema(summary="Modifier une spécialité (PUT)",      tags=["Spécialités"]),
    partial_update=extend_schema(summary="Modifier une spécialité (PATCH)", tags=["Spécialités"]),
    destroy=extend_schema(summary="Supprimer une spécialité (soft)",   tags=["Spécialités"]),
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