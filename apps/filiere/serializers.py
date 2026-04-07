"""
apps/filiere/serializers.py
"""
from rest_framework import serializers
from apps.filiere.models import Filiere


class FiliereSerializer(serializers.ModelSerializer):
    """Sérialisation complète d'une filière (lecture + écriture)."""

    name = serializers.CharField(
        max_length=100,
        help_text="Nom unique de la filière. Ex: Droit, Informatique, Médecine.",
    )

    class Meta:
        model = Filiere
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        return value.strip()


class FiliereMinimalSerializer(serializers.ModelSerializer):
    """Représentation allégée pour les relations imbriquées."""

    class Meta:
        model = Filiere
        fields = ["id", "name"]
