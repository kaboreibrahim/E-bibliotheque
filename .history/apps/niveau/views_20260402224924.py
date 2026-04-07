"""
apps/niveau/views.py
"""
from django.core.exceptions import ValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.niveau.serializers import NiveauSerializer
from apps.niveau.services import NiveauService

_service = NiveauService()


@extend_schema_view(
    list=extend_schema(
        summary="Lister les niveaux",
        tags=["Niveaux"],
        parameters=[
            OpenApiParameter(
                name="filiere",
                description="Filtrer par UUID de filière",
                required=False,
                type=str,
            )
        ],
    ),
    create=extend_schema(summary="Créer un niveau", tags=["Niveaux"]),
    retrieve=extend_schema(summary="Détail d'un niveau", tags=["Niveaux"]),
    destroy=extend_schema(summary="Supprimer un niveau (soft)", tags=["Niveaux"]),
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