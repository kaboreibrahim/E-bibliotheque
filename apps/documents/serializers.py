from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.documents.models import Document
from apps.documents.models.document_type_models import TypeDocument
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


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    type_display = serializers.CharField(source="get_type_display", read_only=True)
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
            "description",
            "file_url",
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

    def get_file_url(self, obj) -> str | None:
        if not obj.file_path:
            return None

        url = obj.file_path.url
        request = self.context.get("request")
        if request is None:
            return url
        return request.build_absolute_uri(url)

    def get_auteur_ou_encadreur(self, obj) -> str:
        if obj.type in {TypeDocument.MEMOIRE, TypeDocument.THESE}:
            return obj.auteur or ""
        return obj.encadreur or ""


class DocumentCreateSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Titre du document.",
    )
    type = serializers.ChoiceField(
        choices=TypeDocument.choices,
        help_text="Type du document : COURS, EXAMEN, MEMOIRE ou THESE.",
    )
    file_path = serializers.FileField(
        help_text="Fichier a televerser via multipart/form-data.",
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
            "description",
            "filiere",
            "niveau",
            "specialite",
            "ue",
            "annee_academique_debut",
            "auteur",
            "encadreur",
        ]

    def validate(self, attrs):
        instance = Document(**attrs)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class DocumentOpenResponseSerializer(serializers.Serializer):
    consultation_id = serializers.UUIDField()
    document = DocumentSerializer()
