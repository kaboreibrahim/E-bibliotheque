"""
apps/consultations/views.py
ViewSets DRF + annotations drf-spectacular (Swagger / ReDoc).

Endpoints exposés :
  GET    /api/v1/consultations/                          → liste (filtrable)
  POST   /api/v1/consultations/vue/                      → enregistrer une vue
  POST   /api/v1/consultations/recherche/                → enregistrer une recherche
  GET    /api/v1/consultations/{id}/                     → détail
  PATCH  /api/v1/consultations/{id}/terminer/            → clôturer une consultation VUE
  DELETE /api/v1/consultations/{id}/                     → soft-delete
  GET    /api/v1/consultations/stats/document/{doc_id}/  → stats d'un document
  GET    /api/v1/consultations/stats/top-documents/      → top 10 documents consultés
  GET    /api/v1/consultations/stats/top-recherches/     → top 10 recherches
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.consultations.models import Consultation
from apps.consultations.serializers import (
    ConsultationRechercheCreateSerializer,
    ConsultationSerializer,
    ConsultationTerminerSerializer,
    ConsultationVueCreateSerializer,
    StatsDocumentSerializer,
    TopDocumentSerializer,
    TopRechercheSerializer,
)
from apps.consultations.services import ConsultationService

_service = ConsultationService()

# ─────────────────────────────────────────────────────────────────────────────


def _get_client_ip(request) -> str | None:
    """Extrait l'IP réelle du client (supporte X-Forwarded-For)."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:500]


# ─────────────────────────────────────────────────────────────────────────────
@extend_schema_view(
    list=extend_schema(
        summary="Lister les consultations",
        tags=["Consultations"],
        parameters=[
            OpenApiParameter(name="user",     description="Filtrer par UUID d'utilisateur",  required=False, type=str),
            OpenApiParameter(name="document", description="Filtrer par UUID de document",     required=False, type=str),
            OpenApiParameter(
                name="type",
                description="Filtrer par type (VUE | RECHERCHE)",
                required=False,
                type=str,
                enum=[c[0] for c in Consultation.TypeConsultation.choices],
            ),
        ],
    ),
    retrieve=extend_schema(summary="Détail d'une consultation",          tags=["Consultations"]),
    destroy=extend_schema(summary="Supprimer une consultation (soft)",   tags=["Consultations"]),
)
class ConsultationViewSet(viewsets.ViewSet):
    """
    Gestion des consultations : vues de documents et recherches effectuées.
    """
    permission_classes = [IsAuthenticated]

    # ── GET /consultations/ ───────────────────────────────────────────────────
    def list(self, request):
        user_id     = request.query_params.get("user")
        document_id = request.query_params.get("document")
        type_c      = request.query_params.get("type")
        try:
            qs = _service.list_consultations(
                user_id=user_id,
                document_id=document_id,
                type_consultation=type_c,
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ConsultationSerializer(qs, many=True).data)

    # ── GET /consultations/{id}/ ──────────────────────────────────────────────
    def retrieve(self, request, pk=None):
        try:
            consultation = _service.get_consultation(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConsultationSerializer(consultation).data)

    # ── DELETE /consultations/{id}/ ───────────────────────────────────────────
    def destroy(self, request, pk=None):
        try:
            _service.supprimer_consultation(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── POST /consultations/vue/ ──────────────────────────────────────────────
    @extend_schema(
        summary="Enregistrer une vue de document",
        tags=["Consultations"],
        request=ConsultationVueCreateSerializer,
        responses={201: ConsultationSerializer},
        description=(
            "Crée une entrée de type VUE. "
            "L'IP et le User-Agent sont extraits automatiquement de la requête."
        ),
    )
    @action(detail=False, methods=["post"], url_path="vue")
    def vue(self, request):
        serializer = ConsultationVueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            consultation = _service.enregistrer_vue(
                document_id=str(vd["document"]),
                user_id=str(vd["user"]) if vd.get("user") else None,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ConsultationSerializer(consultation).data, status=status.HTTP_201_CREATED)

    # ── POST /consultations/recherche/ ────────────────────────────────────────
    @extend_schema(
        summary="Enregistrer une recherche",
        tags=["Consultations"],
        request=ConsultationRechercheCreateSerializer,
        responses={201: ConsultationSerializer},
    )
    @action(detail=False, methods=["post"], url_path="recherche")
    def recherche(self, request):
        serializer = ConsultationRechercheCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            consultation = _service.enregistrer_recherche(
                recherche_query=vd["recherche_query"],
                user_id=str(vd["user"]) if vd.get("user") else None,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ConsultationSerializer(consultation).data, status=status.HTTP_201_CREATED)

    # ── PATCH /consultations/{id}/terminer/ ───────────────────────────────────
    @extend_schema(
        summary="Clôturer une consultation VUE",
        tags=["Consultations"],
        responses={200: ConsultationTerminerSerializer},
        description=(
            "Renseigne fin_consultation = now() et calcule duree_secondes automatiquement. "
            "Ne fonctionne que sur les consultations de type VUE non encore terminées."
        ),
    )
    @action(detail=True, methods=["patch"], url_path="terminer")
    def terminer(self, request, pk=None):
        try:
            consultation = _service.terminer_consultation(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ConsultationTerminerSerializer(consultation).data,
            status=status.HTTP_200_OK,
        )

    # ── GET /consultations/stats/document/{doc_id}/ ───────────────────────────
    @extend_schema(
        summary="Statistiques de consultation d'un document",
        tags=["Consultations – Stats"],
        parameters=[
            OpenApiParameter(name="doc_id", location="path", description="UUID du document", type=str),
        ],
        responses={200: StatsDocumentSerializer},
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"stats/document/(?P<doc_id>[^/.]+)",
        permission_classes=[IsAuthenticated],
    )
    def stats_document(self, request, doc_id=None):
        stats = _service.stats_document(doc_id)
        return Response(StatsDocumentSerializer(stats).data)

    # ── GET /consultations/stats/top-documents/ ───────────────────────────────
    @extend_schema(
        summary="Top documents les plus consultés",
        tags=["Consultations – Stats"],
        parameters=[
            OpenApiParameter(name="limit", description="Nombre de résultats (max 50, défaut 10)", required=False, type=int),
        ],
        responses={200: TopDocumentSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="stats/top-documents",
        permission_classes=[IsAdminUser],
    )
    def top_documents(self, request):
        limit = int(request.query_params.get("limit", 10))
        data  = _service.top_documents(limit)
        return Response(TopDocumentSerializer(data, many=True).data)

    # ── GET /consultations/stats/top-recherches/ ──────────────────────────────
    @extend_schema(
        summary="Top termes de recherche",
        tags=["Consultations – Stats"],
        parameters=[
            OpenApiParameter(name="limit", description="Nombre de résultats (max 50, défaut 10)", required=False, type=int),
        ],
        responses={200: TopRechercheSerializer(many=True)},
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="stats/top-recherches",
        permission_classes=[IsAdminUser],
    )
    def top_recherches(self, request):
        limit = int(request.query_params.get("limit", 10))
        data  = _service.top_recherches(limit)
        return Response(TopRechercheSerializer(data, many=True).data)

    # ── GET /consultations/en-cours/ ──────────────────────────────────────────
    @extend_schema(
        summary="Consultations en cours (non terminées) de l'utilisateur courant",
        tags=["Consultations"],
        parameters=[
            OpenApiParameter(name="user", description="UUID de l'utilisateur", required=True, type=str),
        ],
        responses={200: ConsultationSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="en-cours")
    def en_cours(self, request):
        user_id = request.query_params.get("user")
        if not user_id:
            return Response(
                {"detail": "Le paramètre 'user' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = _service.get_consultations_en_cours(user_id)
        return Response(ConsultationSerializer(qs, many=True).data)