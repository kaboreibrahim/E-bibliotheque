"""
apps/specialites/serializers.py
"""
from rest_framework import serializers
from apps.niveau.serializers import NiveauMinimalSerializer
from apps.specialites.models import Specialite


class SpecialiteSerializer(serializers.ModelSerializer):
    niveau_detail = NiveauMinimalSerializer(source="niveau", read_only=True)
    niveau = serializers.UUIDField(write_only=True)

    # Propriétés calculées exposées en lecture
    est_doctorat    = serializers.BooleanField(read_only=True)
    nb_etudiants    = serializers.IntegerField(read_only=True)
    nb_documents    = serializers.IntegerField(read_only=True)
    nb_ues          = serializers.IntegerField(read_only=True)

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