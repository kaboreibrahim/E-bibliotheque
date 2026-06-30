"""
apps/ue/views.py
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

from apps.ue.serializers import ECUESerializer, UESerializer
from apps.ue.services import ECUEService, UEService

_ue_service = UEService()
_ecue_service = ECUEService()

UE_LIST_EXAMPLE = OpenApiExample(
    "Reponse liste des UE",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "66666666-6666-6666-6666-666666666666",
            "code": "UE-DR-CIV-01",
            "name": "Droit civil des obligations",
            "coef": "5.00",
            "coef_total": "5.00",
            "specialites_detail": [
                {"id": "33333333-3333-3333-3333-333333333333", "name": "Droit prive"},
                {"id": "44444444-4444-4444-4444-444444444444", "name": "Droit public"},
            ],
            "ecues": [
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "code": "ECUE-DR-CIV-01",
                    "name": "Introduction",
                    "coef": "2.00",
                },
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "code": "ECUE-DR-CIV-02",
                    "name": "Approfondissement",
                    "coef": "3.00",
                },
            ],
            "created_at": "2026-04-03T12:00:00Z",
        }
    ],
)

UE_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload creation UE",
    request_only=True,
    value={
        "code": "UE-DR-CIV-01",
        "name": "Droit civil des obligations",
        "specialites": [
            "33333333-3333-3333-3333-333333333333",
            "44444444-4444-4444-4444-444444444444",
        ],
    },
)

UE_RESPONSE_EXAMPLE = OpenApiExample(
    "Reponse UE",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "66666666-6666-6666-6666-666666666666",
        "code": "UE-DR-CIV-01",
        "name": "Droit civil des obligations",
        "coef": "0.00",
        "coef_total": "0.00",
        "specialites_detail": [
            {"id": "33333333-3333-3333-3333-333333333333", "name": "Droit prive"},
            {"id": "44444444-4444-4444-4444-444444444444", "name": "Droit public"},
        ],
        "ecues": [],
        "created_at": "2026-04-03T12:00:00Z",
    },
)

ECUE_LIST_EXAMPLE = OpenApiExample(
    "Reponse liste des ECUE",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "77777777-7777-7777-7777-777777777777",
            "ue_code": "UE-DR-CIV-01",
            "code": "ECUE-DR-CIV-01",
            "name": "Introduction",
            "coef": "2.00",
            "created_at": "2026-04-03T12:10:00Z",
            "updated_at": "2026-04-03T12:10:00Z",
        }
    ],
)

ECUE_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload creation ECUE",
    request_only=True,
    value={
        "ue": "66666666-6666-6666-6666-666666666666",
        "code": "ECUE-DR-CIV-01",
        "name": "Introduction",
        "coef": "2.00",
    },
)

ECUE_RESPONSE_EXAMPLE = OpenApiExample(
    "Reponse ECUE",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "77777777-7777-7777-7777-777777777777",
        "ue_code": "UE-DR-CIV-01",
        "code": "ECUE-DR-CIV-01",
        "name": "Introduction",
        "coef": "2.00",
        "created_at": "2026-04-03T12:10:00Z",
        "updated_at": "2026-04-03T12:10:00Z",
    },
)

UE_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID de l'UE.",
)

ECUE_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID de l'ECUE.",
)


# =============================================================================
# UE
# =============================================================================


@extend_schema_view(
    list=extend_schema(
        summary="Lister les UE",
        tags=["UE"],
        parameters=[
            OpenApiParameter(
                name="specialite",
                description="Filtrer par UUID de specialite",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="q",
                description="Recherche code / intitule",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(response=UESerializer(many=True), description="Liste des UE"),
        },
        examples=[UE_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Creer une UE",
        tags=["UE"],
        request=UESerializer,
        responses={
            201: OpenApiResponse(response=UESerializer, description="UE creee"),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[UE_CREATE_REQUEST_EXAMPLE, UE_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Detail d'une UE",
        tags=["UE"],
        parameters=[UE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=UESerializer, description="Detail complet de l'UE"),
            404: OpenApiResponse(description="UE introuvable"),
        },
        examples=[UE_RESPONSE_EXAMPLE],
    ),
    update=extend_schema(
        summary="Modifier une UE (PUT)",
        tags=["UE"],
        parameters=[UE_ID_PARAMETER],
        request=UESerializer,
        responses={
            200: OpenApiResponse(response=UESerializer, description="UE mise a jour"),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[UE_CREATE_REQUEST_EXAMPLE, UE_RESPONSE_EXAMPLE],
    ),
    partial_update=extend_schema(
        summary="Modifier une UE (PATCH)",
        tags=["UE"],
        parameters=[UE_ID_PARAMETER],
        request=UESerializer,
        responses={
            200: OpenApiResponse(
                response=UESerializer,
                description="UE mise a jour partiellement",
            ),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[
            OpenApiExample(
                "Payload patch UE",
                request_only=True,
                value={"name": "Droit civil special"},
            ),
            UE_RESPONSE_EXAMPLE,
        ],
    ),
    destroy=extend_schema(
        summary="Supprimer une UE (soft)",
        tags=["UE"],
        parameters=[UE_ID_PARAMETER],
        responses={204: OpenApiResponse(description="UE supprimee")},
    ),
)
class UEViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        specialite_id = request.query_params.get("specialite")
        q = request.query_params.get("q", "").strip()
        qs = _ue_service.list_ues(specialite_id=specialite_id, q=q or None)
        return Response(UESerializer(qs, many=True).data)

    def create(self, request):
        serializer = UESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        try:
            ue = _ue_service.create_ue(
                code=vd["code"],
                name=vd["name"],
                specialite_ids=[str(uid) for uid in vd.get("specialites", [])],
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
            "specialite_ids": [str(uid) for uid in vd.get("specialites", [])],
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
        if "specialites" in vd:
            update_fields["specialite_ids"] = [str(uid) for uid in vd["specialites"]]
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

    @extend_schema(
        summary="ECUE d'une UE",
        tags=["UE"],
        parameters=[UE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(
                response=ECUESerializer(many=True),
                description="Liste des ECUE de l'UE",
            ),
        },
        examples=[ECUE_LIST_EXAMPLE],
    )
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
            OpenApiParameter(
                name="ue",
                description="Filtrer par UUID d'UE",
                required=False,
                type=OpenApiTypes.UUID,
            ),
        ],
        responses={
            200: OpenApiResponse(response=ECUESerializer(many=True), description="Liste des ECUE"),
        },
        examples=[ECUE_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Creer un ECUE",
        tags=["ECUE"],
        request=ECUESerializer,
        responses={
            201: OpenApiResponse(response=ECUESerializer, description="ECUE cree"),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[ECUE_CREATE_REQUEST_EXAMPLE, ECUE_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Detail d'un ECUE",
        tags=["ECUE"],
        parameters=[ECUE_ID_PARAMETER],
        responses={
            200: OpenApiResponse(response=ECUESerializer, description="Detail complet de l'ECUE"),
            404: OpenApiResponse(description="ECUE introuvable"),
        },
        examples=[ECUE_RESPONSE_EXAMPLE],
    ),
    update=extend_schema(
        summary="Modifier un ECUE (PUT)",
        tags=["ECUE"],
        parameters=[ECUE_ID_PARAMETER],
        request=ECUESerializer,
        responses={
            200: OpenApiResponse(response=ECUESerializer, description="ECUE mis a jour"),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[ECUE_CREATE_REQUEST_EXAMPLE, ECUE_RESPONSE_EXAMPLE],
    ),
    partial_update=extend_schema(
        summary="Modifier un ECUE (PATCH)",
        tags=["ECUE"],
        parameters=[ECUE_ID_PARAMETER],
        request=ECUESerializer,
        responses={
            200: OpenApiResponse(
                response=ECUESerializer,
                description="ECUE mis a jour partiellement",
            ),
            400: OpenApiResponse(description="Donnees invalides"),
        },
        examples=[
            OpenApiExample("Payload patch ECUE", request_only=True, value={"coef": "3.00"}),
            ECUE_RESPONSE_EXAMPLE,
        ],
    ),
    destroy=extend_schema(
        summary="Supprimer un ECUE (soft)",
        tags=["ECUE"],
        parameters=[ECUE_ID_PARAMETER],
        responses={204: OpenApiResponse(description="ECUE supprime")},
    ),
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
                pk,
                code=vd["code"],
                name=vd["name"],
                coef=vd["coef"],
            )
        except ValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ECUESerializer(ecue).data)

    def partial_update(self, request, pk=None):
        serializer = ECUESerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        update_fields = {key: value for key, value in vd.items() if key != "ue"}
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
