"""
apps/ue/serializers.py
"""
from decimal import Decimal
from rest_framework import serializers
from apps.niveau.serializers import NiveauMinimalSerializer
from apps.ue.models import ECUE, UE


# =============================================================================
# ECUE
# =============================================================================

class ECUESerializer(serializers.ModelSerializer):
    ue = serializers.UUIDField(
        write_only=True,
        help_text="UUID de l'UE parente.",
    )
    ue_code = serializers.CharField(source="ue.code", read_only=True)
    code = serializers.CharField(
        max_length=20,
        help_text="Code court et unique dans l'UE. Ex: ECUE-DR-CIV-01.",
    )
    name = serializers.CharField(
        max_length=200,
        help_text="Intitulé complet de l'ECUE. Ex: Droit civil approfondi.",
    )
    coef = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Coefficient de l'ECUE. Doit être supérieur ou égal à 0.",
    )

    class Meta:
        model  = ECUE
        fields = ["id", "ue", "ue_code", "code", "name", "coef", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_coef(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Le coefficient doit être >= 0.")
        return value


class ECUEInlineSerializer(serializers.ModelSerializer):
    """Utilisé pour afficher les ECUE imbriquées dans l'UE."""
    class Meta:
        model  = ECUE
        fields = ["id", "code", "name", "coef"]


# =============================================================================
# UE
# =============================================================================

class UESerializer(serializers.ModelSerializer):
    niveaux_detail = NiveauMinimalSerializer(source="niveaux", many=True, read_only=True)
    niveaux        = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
        help_text="Liste des UUID des niveaux concernés par l'UE.",
    )
    ecues      = ECUEInlineSerializer(many=True, read_only=True)
    coef_total = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        read_only=True,
        help_text="Somme des coefficients de tous les ECUE de l'UE.",
    )
    code = serializers.CharField(
        max_length=20,
        help_text="Code unique de l'UE. Ex: UE-DR-CIV-01.",
    )
    name = serializers.CharField(
        max_length=200,
        help_text="Intitulé complet de l'UE. Ex: Droit civil des obligations.",
    )

    class Meta:
        model  = UE
        fields = [
            "id", "code", "name", "coef", "coef_total",
            "niveaux", "niveaux_detail",
            "ecues",
            "created_at",
        ]
        read_only_fields = ["id", "coef", "created_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()

    def validate_name(self, value: str) -> str:
        return value.strip()
