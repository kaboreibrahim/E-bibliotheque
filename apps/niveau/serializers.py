"""
apps/niveau/serializers.py
"""
from rest_framework import serializers
from apps.filiere.serializers import FiliereMinimalSerializer
from apps.niveau.models import Niveau


class NiveauSerializer(serializers.ModelSerializer):
    filiere_detail = FiliereMinimalSerializer(source="filiere", read_only=True)
    filiere = serializers.UUIDField(
        write_only=True,
        help_text="UUID de la filière à laquelle rattacher le niveau.",
    )
    name = serializers.ChoiceField(
        choices=Niveau.NiveauChoices.choices,
        help_text="Valeurs autorisées : L1, L2, L3, M1, M2, DOCTORAT.",
    )

    class Meta:
        model = Niveau
        fields = ["id", "filiere", "filiere_detail", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value: str) -> str:
        valid = [c[0] for c in Niveau.NiveauChoices.choices]
        if value not in valid:
            raise serializers.ValidationError(
                f"Valeur invalide. Choix : {', '.join(valid)}."
            )
        return value


class NiveauMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niveau
        fields = ["id", "name"]
