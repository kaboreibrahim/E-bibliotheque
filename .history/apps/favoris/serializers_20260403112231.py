"""
apps/favoris/serializers.py
"""
from rest_framework import serializers

from apps.favoris.models import Favori


# ── Représentations légères des relations ─────────────────────────────────────

class _EtudiantMinimalSerializer(serializers.Serializer):
    id         = serializers.UUIDField()
    full_name  = serializers.SerializerMethodField()
    matricule  = serializers.CharField()

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class _DocumentMinimalSerializer(serializers.Serializer):
    id    = serializers.UUIDField()
    title = serializers.CharField()


# ── Sérialisation principale ──────────────────────────────────────────────────

class FavoriSerializer(serializers.ModelSerializer):
    """Lecture complète d'un favori."""
    etudiant_detail = _EtudiantMinimalSerializer(source="etudiant", read_only=True)
    document_detail = _DocumentMinimalSerializer(source="document", read_only=True)

    # Champs écriture
    etudiant = serializers.UUIDField(write_only=True)
    document = serializers.UUIDField(write_only=True)

    class Meta:
        model  = Favori
        fields = [
            "id",
            "etudiant", "etudiant_detail",
            "document", "document_detail",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class FavoriCreateSerializer(serializers.Serializer):
    """
    Sérialisation dédiée à la création d'un favori.
    Utilisé en POST pour valider uniquement les UUID nécessaires.
    """
    etudiant = serializers.UUIDField()
    document = serializers.UUIDField()


class FavoriToggleResponseSerializer(serializers.Serializer):
    """
    Réponse de l'action toggle (ajout / suppression automatique).
    """
    action    = serializers.ChoiceField(choices=["ajouté", "supprimé"])
    en_favori = serializers.BooleanField()
    favori_id = serializers.UUIDField(allow_null=True)