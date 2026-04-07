"""
apps/specialites/serializers.py
"""
from rest_framework import serializers
from apps.niveau.serializers import NiveauMinimalSerializer
from apps.specialites.models import Specialite


class SpecialiteSerializer(serializers.ModelSerializer):
    niveau_detail = NiveauMinimalSerializer(source="niveau", read_only=True)
    niveau = serializers.UUIDField(
        write_only=True,
        help_text="UUID du niveau auquel rattacher la spécialité.",
    )
    name = serializers.CharField(
        max_length=200,
        help_text="Nom unique dans un même niveau. Ex: Droit des Affaires.",
    )

    # Propriétés calculées exposées en lecture
    est_doctorat    = serializers.BooleanField(read_only=True, help_text="True si la spécialité est rattachée au niveau DOCTORAT.")
    nb_etudiants    = serializers.IntegerField(read_only=True, help_text="Nombre d'étudiants actuellement rattachés à cette spécialité.")
    nb_documents    = serializers.IntegerField(read_only=True, help_text="Nombre de documents liés à cette spécialité.")
    nb_ues          = serializers.IntegerField(read_only=True, help_text="Nombre d'UE liées à cette spécialité.")

    class Meta:
        model  = Specialite
        fields = [
            "id", "name",
            "niveau", "niveau_detail",
            "est_doctorat", "nb_etudiants", "nb_documents", "nb_ues",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return value.strip()


class SpecialiteMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Specialite
        fields = ["id", "name"]
