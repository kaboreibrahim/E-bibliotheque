from rest_framework import serializers

from apps.consultations.repositories import ConsultationRepository
from apps.favoris.repositories import FavoriRepository


class NamedResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class ProfileDocumentSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)


class ProfileFavoriSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    document = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_document(self, obj):
        if not obj.document:
            return None
        return ProfileDocumentSummarySerializer(obj.document).data


class ProfileConsultationSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    type_consultation = serializers.CharField(read_only=True)
    document = serializers.SerializerMethodField()
    recherche_query = serializers.CharField(read_only=True)
    debut_consultation = serializers.DateTimeField(read_only=True)
    fin_consultation = serializers.DateTimeField(read_only=True, allow_null=True)
    duree_secondes = serializers.IntegerField(read_only=True, allow_null=True)
    duree_formatee = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_document(self, obj):
        if not obj.document:
            return None
        return ProfileDocumentSummarySerializer(obj.document).data


class EtudiantOwnProfileSerializer(serializers.Serializer):
    etudiant_id = serializers.UUIDField(source='id', read_only=True)
    matricule = serializers.CharField(read_only=True)
    filiere = serializers.SerializerMethodField()
    niveau = serializers.SerializerMethodField()
    specialite = serializers.SerializerMethodField()
    annee_inscription = serializers.IntegerField(read_only=True)
    statut_compte = serializers.CharField(read_only=True)
    jours_restants = serializers.IntegerField(read_only=True, allow_null=True)
    pourcentage_validite = serializers.IntegerField(read_only=True, allow_null=True)
    compte_active_le = serializers.DateTimeField(read_only=True, allow_null=True)
    compte_expire_le = serializers.DateTimeField(read_only=True, allow_null=True)
    nb_reactivations = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    favoris = serializers.SerializerMethodField()
    consultations = serializers.SerializerMethodField()

    def _serialize_resource(self, instance):
        if not instance:
            return None
        return NamedResourceSerializer(instance).data

    def get_filiere(self, obj):
        return self._serialize_resource(obj.filiere)

    def get_niveau(self, obj):
        return self._serialize_resource(obj.niveau)

    def get_specialite(self, obj):
        return self._serialize_resource(obj.specialite)

    def get_favoris(self, obj):
        favoris = FavoriRepository.get_by_etudiant(str(obj.id))
        return ProfileFavoriSerializer(favoris, many=True).data

    def get_consultations(self, obj):
        consultations = ConsultationRepository.get_by_user(str(obj.user_id))
        return ProfileConsultationSerializer(consultations, many=True).data


class BibliothecaireOwnProfileSerializer(serializers.Serializer):
    bibliothecaire_id = serializers.UUIDField(source='id', read_only=True)
    badge_number = serializers.CharField(read_only=True, allow_null=True)
    date_prise_poste = serializers.DateField(read_only=True, allow_null=True)
    peut_gerer_documents = serializers.BooleanField(read_only=True)
    peut_gerer_utilisateurs = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class PersonneExterneOwnProfileSerializer(serializers.Serializer):
    personne_externe_id = serializers.UUIDField(source='id', read_only=True)
    numero_piece = serializers.CharField(read_only=True)
    profession = serializers.CharField(read_only=True)
    lieu_habitation = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    favoris = serializers.SerializerMethodField()
    consultations = serializers.SerializerMethodField()

    def get_favoris(self, obj):
        return []

    def get_consultations(self, obj):
        consultations = ConsultationRepository.get_by_user(str(obj.user_id))
        return ProfileConsultationSerializer(consultations, many=True).data


class AdminOwnProfileSerializer(serializers.Serializer):
    admin_id = serializers.UUIDField(source='id', read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True, allow_null=True)


class UserOwnProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    phone = serializers.CharField(read_only=True)
    user_type = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    date_of_birth = serializers.DateField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_2fa_enabled = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    profil = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None

        request = self.context.get('request')
        if request is None:
            return obj.avatar.url
        return request.build_absolute_uri(obj.avatar.url)

    def get_profil(self, obj):
        if obj.user_type == obj.UserType.ETUDIANT and hasattr(obj, 'profil_etudiant'):
            return EtudiantOwnProfileSerializer(obj.profil_etudiant).data

        if obj.user_type == obj.UserType.BIBLIOTHECAIRE and hasattr(obj, 'profil_bibliothecaire'):
            return BibliothecaireOwnProfileSerializer(obj.profil_bibliothecaire).data

        if obj.user_type == obj.UserType.PERSONNE_EXTERNE and hasattr(obj, 'profil_personne_externe'):
            return PersonneExterneOwnProfileSerializer(obj.profil_personne_externe).data

        if obj.user_type == obj.UserType.ADMINISTRATEUR:
            return AdminOwnProfileSerializer(obj).data

        return {}


class UserOwnProfileUpdateSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Aucune donnee a mettre a jour n'a ete fournie."
            )
        return attrs
