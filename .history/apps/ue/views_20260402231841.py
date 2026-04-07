"""
apps/ue/views.py
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ue.serializers import ECUESerializer, UESerializer
from apps.ue.services import ECUEService, UEService

_ue_service   = UEService()
_ecue_service = ECUEService()


# =============================================================================
# UE
# =============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Lister les UE",
        tags=["UE"],
        parameters=[
            OpenApiParameter(name="niveau", description="Filtrer par UUID de niveau", required=False, type=str),
            OpenApiParameter(name="q",      description="Recherche code / intitulé",  required=False, type=str),
        ],
    ),
    create=extend_schema(summary="Créer une UE",               tags=["UE"]),
    retrieve=extend_schema(summary="Détail d'une UE",          tags=["UE"]),
    update=extend_schema(summary="Modifier une UE (PUT)",      tags=["UE"]),
    partial_update=extend_schema(summary="Modifier une UE (PATCH)", tags=["UE"]),
    destroy=extend_schema(summary="Supprimer une UE (soft)",   tags=["UE"]),
)
class UEViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        niveau_id = request.query_params.get("niveau")
        q         = request.query_params.get("q", "").strip()
        qs = _ue_service.list_ues(niveau_id=niveau_id, q=q or None)
        return Response(UESerializer(qs, many=True).data)

    def create(self, request):
        serializer = UESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            ue = _ue_service.create_ue(
                code=vd["code"],
                name=vd["name"],
                niveau_ids=[str(uid) for uid in vd.get("niveaux", [])],
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UESerializer(ue).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            ue = _ue_service.get_ue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(UESerializer(ue).data)

    def update(self, request, pk=None):
        serializer = UESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        update_fields = {
            "code": vd["code"],
            "name": vd["name"],
            "niveau_ids": [str(uid) for uid in vd.get("niveaux", [])],
        }
        try:
            ue = _ue_service.update_ue(pk, **update_fields)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UESerializer(ue).data)

    def partial_update(self, request, pk=None):
        serializer = UESerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        update_fields = {}
        if "code" in vd:
            update_fields["code"] = vd["code"]
        if "name" in vd:
            update_fields["name"] = vd["name"]
        if "niveaux" in vd:
            update_fields["niveau_ids"] = [str(uid) for uid in vd["niveaux"]]
        try:
            ue = _ue_service.update_ue(pk, **update_fields) if update_fields else _ue_service.get_ue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UESerializer(ue).data)

    def destroy(self, request, pk=None):
        try:
            _ue_service.delete_ue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Nested : /ues/{id}/ecues/ ─────────────────────────────────────────────
    @extend_schema(summary="ECUE d'une UE", tags=["UE"])
    @action(detail=True, methods=["get"], url_path="ecues")
    def ecues(self, request, pk=None):
        qs = _ecue_service.list_ecues(ue_id=pk)
        return Response(ECUESerializer(qs, many=True).data)


# =============================================================================
# ECUE
# =============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Lister les ECUE",
        tags=["ECUE"],
        parameters=[
            OpenApiParameter(name="ue", description="Filtrer par UUID d'UE", required=False, type=str),
        ],
    ),
    create=extend_schema(summary="Créer un ECUE",              tags=["ECUE"]),
    retrieve=extend_schema(summary="Détail d'un ECUE",         tags=["ECUE"]),
    update=extend_schema(summary="Modifier un ECUE (PUT)",     tags=["ECUE"]),
    partial_update=extend_schema(summary="Modifier un ECUE (PATCH)", tags=["ECUE"]),
    destroy=extend_schema(summary="Supprimer un ECUE (soft)",  tags=["ECUE"]),
)
class ECUEViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        ue_id = request.query_params.get("ue")
        qs = _ecue_service.list_ecues(ue_id=ue_id)
        return Response(ECUESerializer(qs, many=True).data)

    def create(self, request):
        serializer = ECUESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            ecue = _ecue_service.create_ecue(
                ue_id=str(vd["ue"]),
                code=vd["code"],
                name=vd["name"],
                coef=vd["coef"],
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ECUESerializer(ecue).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            ecue = _ecue_service.get_ecue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(ECUESerializer(ecue).data)

    def update(self, request, pk=None):
        serializer = ECUESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            ecue = _ecue_service.update_ecue(
                pk, code=vd["code"], name=vd["name"], coef=vd["coef"]
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ECUESerializer(ecue).data)

    def partial_update(self, request, pk=None):
        serializer = ECUESerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        update_fields = {k: v for k, v in vd.items() if k != "ue"}
        try:
            ecue = _ecue_service.update_ecue(pk, **update_fields) if update_fields else _ecue_service.get_ecue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ECUESerializer(ecue).data)

    def destroy(self, request, pk=None):
        try:
            _ecue_service.delete_ecue(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)