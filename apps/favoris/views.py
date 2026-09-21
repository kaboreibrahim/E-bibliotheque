"""
apps/favoris/views.py
ViewSets DRF + annotations drf-spectacular.
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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.favoris.serializers import (
    FavoriCreateSerializer,
    FavoriSerializer,
    FavoriToggleResponseSerializer,
)
from apps.favoris.services import FavoriService

_service = FavoriService()


def _get_client_ip(request) -> str | None:
    return request.META.get("CLIENT_IP") or request.META.get("REMOTE_ADDR")


def _get_user_agent(request) -> str:
    return (request.META.get("CLIENT_UA") or request.META.get("HTTP_USER_AGENT") or "")[:500]


def _require_own_etudiant_id(request) -> str | None:
    """UUID du profil etudiant de request.user, ou None si ce n'est pas un etudiant."""
    etudiant = getattr(request.user, "profil_etudiant", None)
    return str(etudiant.id) if etudiant else None


_NOT_ETUDIANT_RESPONSE = Response(
    {"detail": "Cette action est reservee aux etudiants."},
    status=status.HTTP_403_FORBIDDEN,
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister mes favoris",
        tags=["Favoris"],
        description="Retourne uniquement les favoris de l'etudiant connecte.",
        parameters=[
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
        summary="Detail d'un favori",
        tags=["Favoris"],
    ),
    destroy=extend_schema(
        summary="Supprimer un favori (soft)",
        tags=["Favoris"],
    ),
)
class FavoriViewSet(viewsets.ViewSet):
    serializer_class = FavoriSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        document_id = request.query_params.get("document")
        qs = _service.list_favoris(etudiant_id=etudiant_id)
        if document_id:
            qs = qs.filter(document_id=document_id)
        return Response(FavoriSerializer(qs, many=True).data)

    def create(self, request):
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        serializer = FavoriCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            favori = _service.ajouter_favori(
                etudiant_id=etudiant_id,
                document_id=str(vd["document"]),
                acteur=request.user,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FavoriSerializer(favori).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        try:
            favori = _service.get_favori(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        if str(favori.etudiant_id) != etudiant_id:
            return Response(
                {"detail": f"Favori introuvable : {pk}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(FavoriSerializer(favori).data)

    def destroy(self, request, pk=None):
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        try:
            favori = _service.get_favori(pk)
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
        if str(favori.etudiant_id) != etudiant_id:
            return Response(
                {"detail": f"Favori introuvable : {pk}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        _service.supprimer_favori(
            pk,
            acteur=request.user,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Basculer un favori (ajout ou suppression automatique)",
        tags=["Favoris"],
        request=FavoriCreateSerializer,
        responses={200: FavoriToggleResponseSerializer},
        description=(
            "Si le document est deja en favori il est supprime. "
            "Sinon il est ajoute."
        ),
    )
    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request):
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        serializer = FavoriCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        document_id = str(vd["document"])
        client_ip = _get_client_ip(request)
        user_agent = _get_user_agent(request)

        if _service.est_en_favori(etudiant_id, document_id):
            try:
                _service.supprimer_favori_par_couple(
                    etudiant_id,
                    document_id,
                    acteur=request.user,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
            except ValidationError as exc:
                return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"action": "supprime", "en_favori": False, "favori_id": None},
                status=status.HTTP_200_OK,
            )

        try:
            favori = _service.ajouter_favori(
                etudiant_id,
                document_id,
                acteur=request.user,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"action": "ajoute", "en_favori": True, "favori_id": str(favori.pk)},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Verifier si un document est dans mes favoris",
        tags=["Favoris"],
        parameters=[
            OpenApiParameter(name="document", description="UUID du document", required=True, type=str),
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
        etudiant_id = _require_own_etudiant_id(request)
        if not etudiant_id:
            return _NOT_ETUDIANT_RESPONSE
        document_id = request.query_params.get("document")

        if not document_id:
            return Response(
                {"detail": "Le parametre 'document' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.favoris.repositories import FavoriRepository

        favori = FavoriRepository.get_by_etudiant_and_document(etudiant_id, document_id)
        return Response(
            {
                "en_favori": favori is not None,
                "favori_id": str(favori.pk) if favori else None,
            }
        )
