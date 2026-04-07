"""
apps/consultations/serializers.py
"""
from rest_framework import serializers

from apps.consultations.models import Consultation


# ── Représentations légères ───────────────────────────────────────────────────

class _UserMinimalSerializer(serializers.Serializer):
    id       = serializers.UUIDField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name()


class _DocumentMinimalSerializer(serializers.Serializer):
    id    = serializers.UUIDField()
    title = serializers.CharField()


# ── Sérialisation principale ──────────────────────────────────────────────────

class ConsultationSerializer(serializers.ModelSerializer):
    """Lecture complète d'une consultation."""
    user_detail     = _UserMinimalSerializer(source="user",     read_only=True)
    document_detail = _DocumentMinimalSerializer(source="document", read_only=True)
    duree_formatee  = serializers.CharField(read_only=True)

    class Meta:
        model  = Consultation
        fields = [
            "id",
            "user", "user_detail",
            "type_consultation",
            "document", "document_detail",
            "recherche_query",
            "debut_consultation", "fin_consultation",
            "duree_secondes", "duree_formatee",
            "ip_address", "user_agent",
            "created_at",
        ]
        read_only_fields = [
            "id", "duree_secondes", "duree_formatee", "created_at",
        ]


# ── Création d'une vue ────────────────────────────────────────────────────────

class ConsultationVueCreateSerializer(serializers.Serializer):
    """
    Payload pour enregistrer une vue de document.
    L'IP et le User-Agent sont extraits de la requête côté vue.
    """
    document = serializers.UUIDField(help_text="UUID du document consulté.")
    user     = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="UUID de l'utilisateur (optionnel pour les visiteurs anonymes).",
    )


# ── Création d'une recherche ──────────────────────────────────────────────────

class ConsultationRechercheCreateSerializer(serializers.Serializer):
    """Payload pour enregistrer une recherche."""
    recherche_query = serializers.CharField(
        max_length=500,
        help_text="Terme saisi dans la barre de recherche.",
    )
    user = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="UUID de l'utilisateur (optionnel).",
    )

    def validate_recherche_query(self, value: str) -> str:
        return value.strip()


# ── Stats ─────────────────────────────────────────────────────────────────────

class StatsDocumentSerializer(serializers.Serializer):
    nb_vues      = serializers.IntegerField()
    duree_moyenne = serializers.FloatField(allow_null=True)
    duree_totale  = serializers.IntegerField(allow_null=True)


class TopDocumentSerializer(serializers.Serializer):
    document_id    = serializers.UUIDField()
    document__title = serializers.CharField()
    nb_vues        = serializers.IntegerField()


class TopRechercheSerializer(serializers.Serializer):
    recherche_query = serializers.CharField()
    nb              = serializers.IntegerField()


# ── Clôture de consultation ───────────────────────────────────────────────────

class ConsultationTerminerSerializer(serializers.Serializer):
    """Réponse renvoyée après terminer() une consultation."""
    id              = serializers.UUIDField()
    fin_consultation = serializers.DateTimeField()
    duree_secondes  = serializers.IntegerField(allow_null=True)
    duree_formatee  = serializers.CharField()