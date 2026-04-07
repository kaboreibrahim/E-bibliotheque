"""
apps/favoris/views.py
ViewSets DRF + annotations drf-spectacular (Swagger / ReDoc).

Endpoints exposés :
  GET    /api/v1/favoris/                     → liste (filtrable par etudiant / document)
  POST   /api/v1/favoris/                     → ajouter un favori
  GET    /api/v1/favoris/{id}/                → détail
  DELETE /api/v1/favoris/{id}/                → supprimer (soft)
  POST   /api/v1/favoris/toggle/              → ajout ou suppression automatique
  GET    /api/v1/favoris/verifier/            → vérifie si un favori existe
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.favoris.serializers import (
    FavoriCreateSerializer,
    FavoriSerializer,
    FavoriToggleResponseSerializer,
)
from apps.favoris.services import FavoriService

_service = FavoriService()


# ─────────────────────────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(
        summary="Lister les favoris",
        tags=["Favoris"],
        parameters=[
            OpenApiParameter(
                name="etudiant",
                description="Filtrer par UUID d'étudiant",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="document",
                description="Filtrer par UUID de document",
                required=False,
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        summary="Ajouter un document aux favoris",
        tags=["Favoris"],
        request=FavoriCreateSerializer,
        responses={201: FavoriSerializer},
    ),
    retrieve=extend_schema(
        summary="Détail d'un favori",
        tags=["Favoris"],
    ),
    destroy=extend_schema(
        summary="Supprimer un favori (soft)",
        tags=["Favoris"],
    ),
)
class FavoriViewSet(viewsets.ViewSet):
    """
    Gestion des favoris : un étudiant peut mettre un document en favori.
    """
    permission_classes = [IsAuthenticated]

    # ── GET /favoris/ ─────────────────────────────────────────────────────────
    def list(self, request):
        etudiant_id = request.query_params.get("etudiant")
        document_id = request.query_params.get("document")
        qs = _service.list_favoris(etudiant_id=etudiant_id, document_id=document_id)
        return Response(FavoriSerializer(qs, many=True).data)

    # ── POST /favoris/ ────────────────────────────────────────────────────────
    def create(self, request):
        serializer = FavoriCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            favori = _service.ajouter_favori(
                etudiant_id=str(vd["etudiant"]),
                document_id=str(vd["document"]),
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FavoriSerializer(favori).data, status=status.HTTP_201_CREATED)

    # ── GET /favoris/{id}/ ────────────────────────────────────────────────────
    def retrieve(self, request, pk=None):
        try:
            favori = _service.get_favori(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(FavoriSerializer(favori).data)

    # ── DELETE /favoris/{id}/ ─────────────────────────────────────────────────
    def destroy(self, request, pk=None):
        try:
            _service.supprimer_favori(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── POST /favoris/toggle/ ─────────────────────────────────────────────────
    @extend_schema(
        summary="Basculer un favori (ajout ou suppression automatique)",
        tags=["Favoris"],
        request=FavoriCreateSerializer,
        responses={200: FavoriToggleResponseSerializer},
        description=(
            "Si le document est déjà en favori → il est supprimé (soft). "
            "S'il ne l'est pas → il est ajouté. "
            "Pratique pour un bouton cœur côté front."
        ),
    )
    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request):
        serializer = FavoriCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        etudiant_id = str(vd["etudiant"])
        document_id = str(vd["document"])

        if _service.est_en_favori(etudiant_id, document_id):
            try:
                _service.supprimer_favori_par_couple(etudiant_id, document_id)
            except ValidationError as exc:
                return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"action": "supprimé", "en_favori": False, "favori_id": None},
                status=status.HTTP_200_OK,
            )

        try:
            favori = _service.ajouter_favori(etudiant_id, document_id)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"action": "ajouté", "en_favori": True, "favori_id": str(favori.pk)},
            status=status.HTTP_200_OK,
        )

    # ── GET /favoris/verifier/?etudiant=...&document=... ──────────────────────
    @extend_schema(
        summary="Vérifier si un document est en favori",
        tags=["Favoris"],
        parameters=[
            OpenApiParameter(name="etudiant", description="UUID de l'étudiant",  required=True, type=str),
            OpenApiParameter(name="document", description="UUID du document",     required=True, type=str),
        ],
        responses={
            200: inline_serializer(
                name="FavoriVerificationResponse",
                fields={
                    "en_favori": serializers.BooleanField(),
                    "favori_id": serializers.UUIDField(allow_null=True),
                },
            )
        },
    )
    @action(detail=False, methods=["get"], url_path="verifier")
    def verifier(self, request):
        etudiant_id = request.query_params.get("etudiant")
        document_id = request.query_params.get("document")

        if not etudiant_id or not document_id:
            return Response(
                {"detail": "Les paramètres 'etudiant' et 'document' sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.favoris.repositories import FavoriRepository
        favori = FavoriRepository.get_by_etudiant_and_document(etudiant_id, document_id)
        return Response({
            "en_favori": favori is not None,
            "favori_id": str(favori.pk) if favori else None,
        })