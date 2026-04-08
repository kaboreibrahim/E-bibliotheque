from rest_framework import serializers


class NamedResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


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


class BibliothecaireOwnProfileSerializer(serializers.Serializer):
    bibliothecaire_id = serializers.UUIDField(source='id', read_only=True)
    badge_number = serializers.CharField(read_only=True, allow_null=True)
    date_prise_poste = serializers.DateField(read_only=True, allow_null=True)
    peut_gerer_documents = serializers.BooleanField(read_only=True)
    peut_gerer_utilisateurs = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


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
