"""
apps/filiere/views.py
ViewSets DRF + annotations drf-spectacular (Swagger / ReDoc).
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.filiere.serializers import FiliereMinimalSerializer, FiliereSerializer
from apps.filiere.services import FiliereService

_service = FiliereService()


# ─────────────────────────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(
        summary="Lister les filières",
        tags=["Filières"],
        parameters=[
            OpenApiParameter(name="q", description="Recherche par nom", required=False, type=str),
        ],
    ),
    create=extend_schema(summary="Créer une filière", tags=["Filières"]),
    retrieve=extend_schema(summary="Détail d'une filière", tags=["Filières"]),
    update=extend_schema(summary="Modifier une filière (PUT)", tags=["Filières"]),
    partial_update=extend_schema(summary="Modifier une filière (PATCH)", tags=["Filières"]),
    destroy=extend_schema(summary="Supprimer une filière (soft)", tags=["Filières"]),
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
    @extend_schema(summary="Niveaux d'une filière", tags=["Filières"])
    @action(detail=True, methods=["get"], url_path="niveaux")
    def niveaux(self, request, pk=None):
        from apps.niveau.serializers import NiveauSerializer
        try:
            filiere = _service.get_filiere(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        serializer = NiveauSerializer(filiere.niveaux.all(), many=True)
        return Response(serializer.data)