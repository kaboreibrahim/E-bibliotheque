from django.core.exceptions import ValidationError
from django.db.models import Count
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.consultations.services import ConsultationService
from apps.documents.models import TypeDocument
from apps.documents.permissions import CanManageDocuments
from apps.documents.serializers import (
    DocumentCreateSerializer,
    DocumentOpenResponseSerializer,
    DocumentSerializer,
    TypeDocumentSerializer,
)
from apps.documents.services import DocumentService

_consultation_service = ConsultationService()
_service = DocumentService(consultation_service=_consultation_service)

TYPE_DOCUMENT_RESPONSE_EXAMPLE = OpenApiExample(
    "Reponse type de document",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "12121212-1212-1212-1212-121212121212",
        "code": "COURS",
        "name": "Cours",
        "nb_documents": 8,
        "created_at": "2026-04-03T09:30:00Z",
        "updated_at": "2026-04-03T09:30:00Z",
    },
)

DOCUMENT_ID_PARAMETER = OpenApiParameter(
    name="id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID du document.",
)

DOCUMENT_LIST_PARAMETERS = [
    OpenApiParameter(
        name="type",
        description="Filtrer par code de type de document. Exemples : COURS, MEMOIRE, RAPPORT.",
        required=False,
        type=str,
    ),
    OpenApiParameter(
        name="filiere",
        description="Filtrer par UUID de filiere.",
        required=False,
        type=OpenApiTypes.UUID,
    ),
    OpenApiParameter(
        name="niveau",
        description="Filtrer par UUID de niveau.",
        required=False,
        type=OpenApiTypes.UUID,
    ),
    OpenApiParameter(
        name="specialite",
        description="Filtrer par UUID de specialite.",
        required=False,
        type=OpenApiTypes.UUID,
    ),
    OpenApiParameter(
        name="ue",
        description="Filtrer par UUID d'ECUE.",
        required=False,
        type=OpenApiTypes.UUID,
    ),
    OpenApiParameter(
        name="ajoute_par",
        description="Filtrer par UUID de l'utilisateur ayant ajoute le document.",
        required=False,
        type=OpenApiTypes.UUID,
    ),
    OpenApiParameter(
        name="annee_academique_debut",
        description="Filtrer par annee academique de debut.",
        required=False,
        type=int,
    ),
    OpenApiParameter(
        name="search",
        description="Recherche sur titre, auteur, encadreur, description, specialite ou UE.",
        required=False,
        type=str,
    ),
]

DOCUMENT_ERROR_RESPONSE = inline_serializer(
    "DocumentErrorResponse",
    fields={
        "detail": drf_serializers.CharField(),
    },
)

DOCUMENT_LIST_EXAMPLE = OpenApiExample(
    "Reponse liste des documents",
    response_only=True,
    status_codes=["200"],
    value=[
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "title": "Cours de procedure civile",
            "type": "COURS",
            "type_display": "Cours",
            "type_detail": {
                "id": "12121212-1212-1212-1212-121212121212",
                "code": "COURS",
                "name": "Cours",
            },
            "description": "Support du semestre 1",
            "file_name": "procedure-civile.pdf",
            "file_mime_type": "application/pdf",
            "file_base64": None,
            "file_data_uri": None,
            "filiere": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "filiere_detail": {
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "name": "Droit",
            },
            "niveau": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "niveau_detail": {
                "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "name": "L1",
            },
            "specialite": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "specialite_detail": {
                "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "name": "Contentieux L1",
            },
            "ue": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "ue_detail": {
                "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "code": "ECUE-DR-001",
                "name": "Procedure civile",
            },
            "annee_academique_debut": 2024,
            "annee_academique": "2024-2025",
            "auteur": "",
            "encadreur": "Pr. Konan",
            "auteur_ou_encadreur": "Pr. Konan",
            "ajoute_par": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "ajoute_par_detail": {
                "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "email": "admin@example.com",
                "full_name": "Admin Doc",
            },
            "nb_consultations": 12,
            "nb_favoris": 3,
            "created_at": "2026-04-03T10:00:00Z",
            "updated_at": "2026-04-03T10:00:00Z",
        }
    ],
)

DOCUMENT_CREATE_REQUEST_EXAMPLE = OpenApiExample(
    "Payload creation document en Base64",
    request_only=True,
    value={
        "title": "Sujet d examen droit civil",
        "type": "EXAMEN",
        "file_base64": "data:application/pdf;base64,ZXhhbQ==",
        "file_name": "examen-droit-civil.pdf",
        "file_mime_type": "application/pdf",
        "description": "Session normale 2025",
        "filiere": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "niveau": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "specialite": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "ue": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "annee_academique_debut": 2025,
        "auteur": "",
        "encadreur": "Sujet Session 1",
    },
)

DOCUMENT_RESPONSE_EXAMPLE = OpenApiExample(
    "Reponse document",
    response_only=True,
    status_codes=["200", "201"],
    value={
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "title": "Sujet d examen droit civil",
        "type": "EXAMEN",
        "type_display": "Examen",
        "type_detail": {
            "id": "34343434-3434-3434-3434-343434343434",
            "code": "EXAMEN",
            "name": "Examen",
        },
        "description": "Session normale 2025",
        "file_name": "examen-droit-civil.pdf",
        "file_mime_type": "application/pdf",
        "file_base64": "ZXhhbQ==",
        "file_data_uri": "data:application/pdf;base64,ZXhhbQ==",
        "filiere": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "filiere_detail": {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "name": "Droit",
        },
        "niveau": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "niveau_detail": {
            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "name": "L1",
        },
        "specialite": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "specialite_detail": {
            "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            "name": "Contentieux L1",
        },
        "ue": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "ue_detail": {
            "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "code": "ECUE-DR-001",
            "name": "Procedure civile",
        },
        "annee_academique_debut": 2025,
        "annee_academique": "2025-2026",
        "auteur": "",
        "encadreur": "Sujet Session 1",
        "auteur_ou_encadreur": "Sujet Session 1",
        "ajoute_par": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "ajoute_par_detail": {
            "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "email": "admin@example.com",
            "full_name": "Admin Doc",
        },
        "nb_consultations": 0,
        "nb_favoris": 0,
        "created_at": "2026-04-03T10:15:00Z",
        "updated_at": "2026-04-03T10:15:00Z",
    },
)

DOCUMENT_OPEN_RESPONSE_EXAMPLE = OpenApiExample(
    "Reponse ouverture document",
    response_only=True,
    status_codes=["200"],
    value={
        "consultation_id": "99999999-9999-9999-9999-999999999999",
        "document": DOCUMENT_RESPONSE_EXAMPLE.value,
    },
)

DOCUMENT_ERROR_EXAMPLE = OpenApiExample(
    "Erreur document introuvable",
    response_only=True,
    status_codes=["404"],
    value={"detail": "Document introuvable : aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa."},
)


def _get_client_ip(request) -> str | None:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:500]


@extend_schema_view(
    list=extend_schema(
        summary="Lister les types de documents",
        tags=["Types de documents"],
        responses={
            200: OpenApiResponse(
                response=TypeDocumentSerializer(many=True),
                description="Liste des types de documents.",
            ),
        },
        examples=[TYPE_DOCUMENT_RESPONSE_EXAMPLE],
    ),
    create=extend_schema(
        summary="Creer un type de document",
        tags=["Types de documents"],
        request=TypeDocumentSerializer,
        responses={
            201: OpenApiResponse(
                response=TypeDocumentSerializer,
                description="Type de document cree.",
            ),
            400: OpenApiResponse(description="Donnees invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
        },
        examples=[
            OpenApiExample(
                "Payload creation type",
                request_only=True,
                value={"code": "RAPPORT", "name": "Rapport"},
            ),
            TYPE_DOCUMENT_RESPONSE_EXAMPLE,
        ],
    ),
    retrieve=extend_schema(
        summary="Detail d'un type de document",
        tags=["Types de documents"],
        responses={
            200: OpenApiResponse(
                response=TypeDocumentSerializer,
                description="Detail d'un type de document.",
            ),
            404: OpenApiResponse(description="Type de document introuvable."),
        },
        examples=[TYPE_DOCUMENT_RESPONSE_EXAMPLE],
    ),
    update=extend_schema(tags=["Types de documents"]),
    partial_update=extend_schema(tags=["Types de documents"]),
    destroy=extend_schema(tags=["Types de documents"]),
)
class TypeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = TypeDocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = TypeDocument.objects.all()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), CanManageDocuments()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return (
            TypeDocument.objects
            .annotate(_nb_documents=Count("documents", distinct=True))
            .order_by("name")
        )


@extend_schema_view(
    list=extend_schema(
        summary="Lister les documents",
        tags=["Documents"],
        parameters=DOCUMENT_LIST_PARAMETERS,
        responses={
            200: OpenApiResponse(
                response=DocumentSerializer(many=True),
                description="Liste des documents.",
            ),
            400: OpenApiResponse(
                response=DOCUMENT_ERROR_RESPONSE,
                description="Filtre invalide.",
            ),
        },
        examples=[DOCUMENT_LIST_EXAMPLE],
    ),
    create=extend_schema(
        summary="Creer un document",
        tags=["Documents"],
        request=DocumentCreateSerializer,
        description=(
            "Creation d'un document via `multipart/form-data` avec `file_path` ou via "
            "`application/json` avec `file_base64`. Le contenu est stocke en Base64 en base. "
            "Reserve aux administrateurs et aux bibliothecaires ayant "
            "`peut_gerer_documents = true`."
        ),
        responses={
            201: OpenApiResponse(
                response=DocumentSerializer,
                description="Document cree.",
            ),
            400: OpenApiResponse(description="Donnees invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
        },
        examples=[DOCUMENT_CREATE_REQUEST_EXAMPLE, DOCUMENT_RESPONSE_EXAMPLE],
    ),
    retrieve=extend_schema(
        summary="Detail d'un document",
        tags=["Documents"],
        parameters=[DOCUMENT_ID_PARAMETER],
        responses={
            200: OpenApiResponse(
                response=DocumentSerializer,
                description="Detail complet du document.",
            ),
            404: OpenApiResponse(
                response=DOCUMENT_ERROR_RESPONSE,
                description="Document introuvable.",
            ),
        },
        examples=[DOCUMENT_RESPONSE_EXAMPLE, DOCUMENT_ERROR_EXAMPLE],
    ),
    destroy=extend_schema(
        summary="Supprimer un document (soft delete)",
        tags=["Documents"],
        parameters=[DOCUMENT_ID_PARAMETER],
        description=(
            "Suppression logique du document. Reserve aux administrateurs et "
            "aux bibliothecaires ayant `peut_gerer_documents = true`."
        ),
        responses={
            204: OpenApiResponse(description="Document supprime."),
            403: OpenApiResponse(description="Permission insuffisante."),
            404: OpenApiResponse(
                response=DOCUMENT_ERROR_RESPONSE,
                description="Document introuvable.",
            ),
        },
        examples=[DOCUMENT_ERROR_EXAMPLE],
    ),
)
class DocumentViewSet(viewsets.ViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in {"create", "destroy"}:
            return [IsAuthenticated(), CanManageDocuments()]
        return [IsAuthenticated()]

    def list(self, request):
        try:
            documents = _service.list_documents(
                user=request.user,
                type_document=request.query_params.get("type"),
                filiere_id=request.query_params.get("filiere"),
                niveau_id=request.query_params.get("niveau"),
                specialite_id=request.query_params.get("specialite"),
                ue_id=request.query_params.get("ue"),
                ajoute_par_id=request.query_params.get("ajoute_par"),
                annee_academique_debut=request.query_params.get(
                    "annee_academique_debut"
                ),
                search=request.query_params.get("search", ""),
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentSerializer(
            documents,
            many=True,
            context={"request": request, "include_file_content": False},
        )
        return Response(serializer.data)

    def create(self, request):
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = _service.create_document(
                data=serializer.validated_data,
                ajoute_par=request.user,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or {"detail": exc.messages}
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)

        read_serializer = DocumentSerializer(
            document,
            context={"request": request, "include_file_content": True},
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            document = _service.get_document(pk, user=request.user)
        except ValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DocumentSerializer(
            document,
            context={"request": request, "include_file_content": True},
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Ouvrir un document",
        tags=["Documents"],
        parameters=[DOCUMENT_ID_PARAMETER],
        description=(
            "Retourne les informations du document et enregistre automatiquement "
            "une consultation de type VUE pour l'utilisateur courant."
        ),
        responses={
            200: OpenApiResponse(
                response=DocumentOpenResponseSerializer,
                description="Document ouvert et consultation creee.",
            ),
            404: OpenApiResponse(
                response=DOCUMENT_ERROR_RESPONSE,
                description="Document introuvable.",
            ),
        },
        examples=[DOCUMENT_OPEN_RESPONSE_EXAMPLE, DOCUMENT_ERROR_EXAMPLE],
    )
    @action(detail=True, methods=["get"], url_path="ouvrir")
    def ouvrir(self, request, pk=None):
        try:
            document, consultation = _service.ouvrir_document(
                document_id=pk,
                user=request.user,
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            status_code = (
                status.HTTP_404_NOT_FOUND
                if "introuvable" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": exc.message}, status=status_code)

        serializer = DocumentSerializer(
            document,
            context={"request": request, "include_file_content": True},
        )
        return Response(
            {
                "consultation_id": str(consultation.pk),
                "document": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        try:
            _service.supprimer_document(
                document_id=pk,
                supprime_par=request.user,
                ip_address=_get_client_ip(request),
                user_agent=_get_user_agent(request),
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.message},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
