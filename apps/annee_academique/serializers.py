"""
apps/annee_academique/serializers.py
"""
from rest_framework import serializers

from apps.annee_academique.models import AnneeAcademique


class AnneeAcademiqueSerializer(serializers.ModelSerializer):
    """Sérialisation complète d'une année académique (lecture + écriture)."""

    libelle = serializers.CharField(read_only=True)
    date_debut = serializers.DateField(
        required=False,
        help_text="Date de début de l'année académique. Format: YYYY-MM-DD.",
    )
    date_fin = serializers.DateField(
        required=False,
        help_text="Date de fin de l'année académique. Format: YYYY-MM-DD.",
    )
    est_courante = serializers.BooleanField(
        required=False,
        help_text=(
            "Si true, cette année devient l'année courante et toutes les "
            "autres années repassent automatiquement à false."
        ),
    )

    class Meta:
        model = AnneeAcademique
        fields = [
            "id",
            "libelle",
            "date_debut",
            "date_fin",
            "est_courante",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "libelle", "created_at", "updated_at"]

    def validate(self, attrs):
        date_debut = attrs.get("date_debut", getattr(self.instance, "date_debut", None))
        date_fin = attrs.get("date_fin", getattr(self.instance, "date_fin", None))

        if not self.instance:
            if not date_debut:
                raise serializers.ValidationError(
                    {"date_debut": "La date de début est obligatoire."}
                )
            if not date_fin:
                raise serializers.ValidationError(
                    {"date_fin": "La date de fin est obligatoire."}
                )

        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError(
                {"date_fin": "La date de fin doit être postérieure à la date de début."}
            )
        return attrs
