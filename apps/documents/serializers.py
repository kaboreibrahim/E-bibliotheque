from collections.abc import Mapping
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.documents.models import Document, TypeDocument
from apps.documents.utils import (
    build_document_file_name,
    extract_document_file_metadata,
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
        fields = ["id", "code", "name", "ordre"]


class NiveauMinimalSerializer(serializers.ModelSerializer):
    filiere_name = serializers.CharField(source="filiere.name", read_only=True)

    class Meta:
        model = Niveau
        fields = ["id", "name", "filiere_name"]


class TypeDocumentSerializer(serializers.ModelSerializer):
    nb_documents = serializers.SerializerMethodField()
    niveaux = NiveauMinimalSerializer(many=True, read_only=True)
    niveaux_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Niveau.objects.all(),
        source='niveaux',
        write_only=True,
        required=False,
    )

    class Meta:
        model = TypeDocument
        fields = [
            "id", "code", "name", "ordre", "niveaux", "niveaux_ids",
            "nb_documents", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "nb_documents", "created_at", "updated_at"]

    def get_nb_documents(self, obj) -> int:
        if hasattr(obj, '_nb_documents'):
            return obj._nb_documents
        return obj.documents.count()

    def validate_code(self, value: str) -> str:
        normalized = TypeDocument.normalize_code(value)
        if not normalized:
            raise serializers.ValidationError("Le code du type de document est obligatoire.")
        return normalized

    def validate_name(self, value: str) -> str:
        return value.strip()

    def create(self, validated_data):
        niveaux = validated_data.pop('niveaux', [])
        instance = super().create(validated_data)
        if niveaux:
            instance.niveaux.set(niveaux)
        return instance

    def update(self, instance, validated_data):
        niveaux = validated_data.pop('niveaux', None)
        instance = super().update(instance, validated_data)
        if niveaux is not None:
            instance.niveaux.set(niveaux)
        return instance


class DocumentSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type.code", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    type_detail = TypeDocumentMinimalSerializer(source="type", read_only=True)
    annee_academique = serializers.CharField(read_only=True)
    nb_consultations = serializers.IntegerField(source="_nb_consultations", read_only=True)
    nb_favoris = serializers.IntegerField(source="_nb_favoris", read_only=True)
    file_size = serializers.SerializerMethodField()
    file_stream_url = serializers.SerializerMethodField()

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
            "file_size",
            "file_stream_url",
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
            "ajoute_par",
            "ajoute_par_detail",
            "nb_consultations",
            "nb_favoris",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_file_size(self, obj) -> int | None:
        return obj.file_size

    def get_file_stream_url(self, obj) -> str | None:
        if not obj.file_path:
            return None

        request = self.context.get("request")
        return reverse("document-fichier", kwargs={"pk": obj.pk}, request=request)

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
        required=True,
        write_only=True,
        help_text="Fichier a televerser via multipart/form-data.",
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

    class Meta:
        model = Document
        fields = [
            "title",
            "type",
            "file_path",
            "file_name",
            "file_mime_type",
            "description",
            "filiere",
            "niveau",
            "specialite",
            "ue",
            "annee_academique_debut",
            "auteur",
        ]

    def validate_type(self, value: str) -> TypeDocument:
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
        upload = attrs.get("file_path")

        if not upload:
            raise serializers.ValidationError(
                {
                    "file_path": "Le fichier du document est obligatoire.",
                }
            )

        detected_file_name, detected_mime_type = extract_document_file_metadata(upload)
        attrs["file_name"] = Path(attrs.get("file_name") or detected_file_name).name
        attrs["file_mime_type"] = attrs.get("file_mime_type") or detected_mime_type

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


class DocumentDashboardStatsSerializer(serializers.Serializer):
    documents_count = serializers.IntegerField(min_value=0)
    documents_with_file_count = serializers.IntegerField(min_value=0)
    total_file_size = serializers.IntegerField(min_value=0)
    total_file_size_mb = serializers.FloatField(min_value=0)
    total_file_size_display = serializers.CharField()
    server_disk_capacity_mb = serializers.IntegerField(min_value=0)
    server_disk_capacity_bytes = serializers.IntegerField(min_value=0)
    server_disk_capacity_display = serializers.CharField()
    remaining_storage_mb = serializers.FloatField(min_value=0)
    remaining_storage_bytes = serializers.IntegerField(min_value=0)
    remaining_storage_display = serializers.CharField()
    used_storage_percentage = serializers.FloatField(min_value=0)
