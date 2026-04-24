from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.documents.models import Document, TypeDocument
from apps.documents.utils import (
    DEFAULT_DOCUMENT_MIME_TYPE,
    build_document_file_name,
    encode_uploaded_document,
    normalize_base64_document,
)
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.models import ECUE


class _DocumentUserMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.get_full_name()


class _DocumentFiliereMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _DocumentNiveauMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _DocumentSpecialiteMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _DocumentECUEMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()


class TypeDocumentMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeDocument
        fields = ["id", "code", "name"]


class TypeDocumentSerializer(serializers.ModelSerializer):
    nb_documents = serializers.IntegerField(source="_nb_documents", read_only=True)

    class Meta:
        model = TypeDocument
        fields = ["id", "code", "name", "nb_documents", "created_at", "updated_at"]
        read_only_fields = ["id", "nb_documents", "created_at", "updated_at"]

    def validate_code(self, value: str) -> str:
        normalized = TypeDocument.normalize_code(value)
        if not normalized:
            raise serializers.ValidationError("Le code du type de document est obligatoire.")
        return normalized

    def validate_name(self, value: str) -> str:
        return value.strip()


class DocumentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type.code", read_only=True)
    file_base64 = serializers.SerializerMethodField()
    file_data_uri = serializers.SerializerMethodField()
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    type_detail = TypeDocumentMinimalSerializer(source="type", read_only=True)
    annee_academique = serializers.CharField(read_only=True)
    auteur_ou_encadreur = serializers.SerializerMethodField()
    nb_consultations = serializers.IntegerField(source="_nb_consultations", read_only=True)
    nb_favoris = serializers.IntegerField(source="_nb_favoris", read_only=True)

    filiere_detail = _DocumentFiliereMinimalSerializer(source="filiere", read_only=True)
    niveau_detail = _DocumentNiveauMinimalSerializer(source="niveau", read_only=True)
    specialite_detail = _DocumentSpecialiteMinimalSerializer(source="specialite", read_only=True)
    ue_detail = _DocumentECUEMinimalSerializer(source="ue", read_only=True)
    ajoute_par_detail = _DocumentUserMinimalSerializer(source="ajoute_par", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "type",
            "type_display",
            "type_detail",
            "description",
            "file_name",
            "file_mime_type",
            "file_base64",
            "file_data_uri",
            "filiere",
            "filiere_detail",
            "niveau",
            "niveau_detail",
            "specialite",
            "specialite_detail",
            "ue",
            "ue_detail",
            "annee_academique_debut",
            "annee_academique",
            "auteur",
            "encadreur",
            "auteur_ou_encadreur",
            "ajoute_par",
            "ajoute_par_detail",
            "nb_consultations",
            "nb_favoris",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _include_file_content(self) -> bool:
        return bool(self.context.get("include_file_content"))

    def get_file_base64(self, obj) -> str | None:
        if not self._include_file_content():
            return None
        return obj.file_base64

    def get_file_data_uri(self, obj) -> str | None:
        if not self._include_file_content():
            return None
        return obj.file_data_uri

    def get_auteur_ou_encadreur(self, obj) -> str:
        if TypeDocument.requires_auteur(obj.type):
            return obj.auteur or ""
        return obj.encadreur or ""


class DocumentCreateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Titre du document.",
    )
    type = serializers.CharField(
        max_length=100,
        help_text=(
            "Code d'un type de document existant. Exemples : COURS, EXAMEN, "
            "MEMOIRE ou THESE."
        ),
    )
    file_path = serializers.FileField(
        required=False,
        write_only=True,
        help_text="Fichier a televerser via multipart/form-data. Il sera stocke en Base64.",
    )
    file_base64 = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Contenu du document en Base64. Le format data URI est accepte.",
    )
    file_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Nom du fichier a conserver en base.",
    )
    file_mime_type = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Type MIME du document. Ex: application/pdf.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description libre du document.",
    )
    filiere = serializers.PrimaryKeyRelatedField(
        queryset=Filiere.objects.all(),
        required=False,
        allow_null=True,
        help_text="UUID de la filiere rattachee au document.",
    )
    niveau = serializers.PrimaryKeyRelatedField(
        queryset=Niveau.objects.all(),
        required=False,
        allow_null=True,
        help_text="UUID du niveau rattache au document.",
    )
    specialite = serializers.PrimaryKeyRelatedField(
        queryset=Specialite.objects.all(),
        required=False,
        allow_null=True,
        help_text="UUID de la specialite. Requis pour les niveaux qui l'imposent.",
    )
    ue = serializers.PrimaryKeyRelatedField(
        queryset=ECUE.objects.all(),
        required=False,
        allow_null=True,
        help_text="UUID de l'ECUE concernee.",
    )
    annee_academique_debut = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Annee de debut. Exemple: 2024 pour 2024-2025.",
    )
    auteur = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Auteur du document. Requis pour MEMOIRE et THESE.",
    )
    encadreur = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Encadreur ou sujet. Requis pour COURS et EXAMEN.",
    )

    class Meta:
        model = Document
        fields = [
            "title",
            "type",
            "file_path",
            "file_base64",
            "file_name",
            "file_mime_type",
            "description",
            "filiere",
            "niveau",
            "specialite",
            "ue",
            "annee_academique_debut",
            "auteur",
            "encadreur",
        ]

    def validate_type(self, value: str) -> str:
        normalized = TypeDocument.normalize_code(value)
        if not normalized:
            raise serializers.ValidationError("Le type de document est obligatoire.")
        type_document = TypeDocument.objects.filter(code=normalized).first()
        if not type_document:
            raise serializers.ValidationError(
                "Type de document introuvable. Creez-le d'abord dans la liste des types."
            )
        return type_document

    def validate(self, attrs):
        upload = attrs.pop("file_path", None)
        raw_base64 = attrs.get("file_base64")

        if upload and raw_base64:
            raise serializers.ValidationError(
                {
                    "file_path": "Fournissez soit un fichier, soit un contenu Base64, pas les deux.",
                    "file_base64": "Fournissez soit un fichier, soit un contenu Base64, pas les deux.",
                }
            )

        if not upload and not raw_base64:
            raise serializers.ValidationError(
                {
                    "file_path": "Un fichier ou un contenu Base64 est obligatoire.",
                    "file_base64": "Un fichier ou un contenu Base64 est obligatoire.",
                }
            )

        if upload:
            encoded_content, detected_file_name, detected_mime_type = encode_uploaded_document(upload)
            attrs["file_base64"] = encoded_content
            attrs["file_name"] = attrs.get("file_name") or detected_file_name
            attrs["file_mime_type"] = attrs.get("file_mime_type") or detected_mime_type
        else:
            try:
                normalized_base64, detected_mime_type = normalize_base64_document(raw_base64)
            except ValueError as exc:
                raise serializers.ValidationError({"file_base64": str(exc)}) from exc

            attrs["file_base64"] = normalized_base64
            attrs["file_mime_type"] = (
                attrs.get("file_mime_type")
                or detected_mime_type
                or DEFAULT_DOCUMENT_MIME_TYPE
            )

        if not attrs.get("file_name"):
            attrs["file_name"] = build_document_file_name(
                attrs.get("title", ""),
                attrs.get("file_mime_type"),
            )

        instance = Document(**attrs)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            detail = exc.message_dict
            if not isinstance(detail, Mapping):
                detail = {"detail": exc.messages}
            raise serializers.ValidationError(detail)
        return attrs


class DocumentOpenResponseSerializer(serializers.Serializer):
    consultation_id = serializers.UUIDField()
    document = DocumentSerializer()
