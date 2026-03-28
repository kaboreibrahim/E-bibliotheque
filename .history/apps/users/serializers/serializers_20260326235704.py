"""
=============================================================================
 apps/users/serializers/auth_serializers.py
 Serializers pour l'authentification (login, OTP, TOTP, reset password)
=============================================================================
"""

import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


# =============================================================================
# 🔐  AUTH SERIALIZERS
# =============================================================================

class LoginSerializer(serializers.Serializer):
    """Connexion par email + password."""
    email    = serializers.EmailField(
        help_text="Adresse email du compte."
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mot de passe."
    )

    def validate_email(self, value):
        return value.lower().strip()


class TOTPVerifySerializer(serializers.Serializer):
    """Validation du code Google Authenticator (étape 2 Admin/Biblio)."""
    user_id   = serializers.UUIDField(
        help_text="UUID de l'utilisateur retourné lors de l'étape 1."
    )
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code à 6 chiffres de Google Authenticator."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code TOTP doit contenir uniquement des chiffres.")
        return value


class TOTPConfirmSetupSerializer(serializers.Serializer):
    """Confirmation de la configuration du TOTP (premier scan du QR code)."""
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code de confirmation après scan du QR code."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code TOTP doit contenir uniquement des chiffres.")
        return value


class OTPSendSerializer(serializers.Serializer):
    """Demande d'envoi d'un code OTP."""
    type_code = serializers.ChoiceField(
        choices=['activation', 'password_reset', 'email_change', 'code_OTP'],
        help_text="Type de code OTP à envoyer."
    )
    email = serializers.EmailField(
        required=False,
        help_text="Email de destination (optionnel — utilise l'email du compte par défaut)."
    )


class OTPVerifySerializer(serializers.Serializer):
    """Vérification d'un code OTP."""
    code      = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code OTP à 6 chiffres reçu par email."
    )
    type_code = serializers.ChoiceField(
        choices=['activation', 'password_reset', 'email_change', 'code_OTP'],
        help_text="Type du code OTP à vérifier."
    )

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code OTP doit contenir uniquement des chiffres.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Nouveau mot de passe après vérification OTP reset."""
    new_password  = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Nouveau mot de passe (min. 8 caractères)."
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du nouveau mot de passe."
    )

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        try:
            validate_password(data['new_password'])
        except Exception as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return data


class RefreshTokenSerializer(serializers.Serializer):
    """Rafraîchissement du token d'accès."""
    refresh = serializers.CharField(help_text="Token de rafraîchissement JWT.")


class LogoutSerializer(serializers.Serializer):
    """Déconnexion — révocation du refresh token."""
    refresh = serializers.CharField(help_text="Token de rafraîchissement à révoquer.")


# =============================================================================
# 📄  USER SERIALIZERS — apps/users/serializers/user_serializers.py
# =============================================================================

from apps.users.models.user_models import User


class UserListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes."""

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'user_type', 'is_active',
            'is_2fa_enabled', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un utilisateur."""
    full_name        = serializers.SerializerMethodField()
    requires_2fa     = serializers.SerializerMethodField()
    profil_etudiant  = serializers.SerializerMethodField()
    profil_biblio    = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'user_type', 'avatar', 'date_of_birth',
            'is_active', 'is_staff', 'is_2fa_enabled',
            'requires_2fa', 'totp_verified_at',
            'created_at', 'updated_at',
            'profil_etudiant', 'profil_biblio',
        ]
        read_only_fields = [
            'id', 'is_staff', 'totp_verified_at',
            'created_at', 'updated_at',
            'full_name', 'requires_2fa',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_requires_2fa(self, obj):
        return obj.requires_2fa

    def get_profil_etudiant(self, obj):
        if obj.user_type != 'ETUDIANT':
            return None
        try:
            e = obj.profil_etudiant
            return {
                'matricule':      e.matricule,
                'filiere':        str(e.filiere) if e.filiere else None,
                'niveau':         str(e.niveau) if e.niveau else None,
                'specialite':     str(e.specialite) if e.specialite else None,
                'statut_compte':  e.statut_compte,
                'jours_restants': e.jours_restants,
                'pourcentage':    e.pourcentage_validite,
                'compte_expire_le': e.compte_expire_le.isoformat() if e.compte_expire_le else None,
            }
        except Exception:
            return None

    def get_profil_biblio(self, obj):
        if obj.user_type != 'BIBLIOTHECAIRE':
            return None
        try:
            b = obj.profil_bibliothecaire
            return {
                'badge_number':             b.badge_number,
                'peut_gerer_documents':    b.peut_gerer_documents,
                'peut_gerer_utilisateurs': b.peut_gerer_utilisateurs,
                'date_prise_poste':        str(b.date_prise_poste) if b.date_prise_poste else None,
            }
        except Exception:
            return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Création d'un nouvel utilisateur."""
    password         = serializers.CharField(
        write_only=True, min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model  = User
        fields = [
            'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone',
            'user_type', 'date_of_birth', 'avatar',
        ]

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return phone

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    """Mise à jour partielle d'un utilisateur (PATCH)."""

    class Meta:
        model  = User
        fields = [
            'first_name', 'last_name', 'phone',
            'avatar', 'date_of_birth',
        ]

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return phone


class ChangePasswordSerializer(serializers.Serializer):
    """Changement de mot de passe (utilisateur connecté)."""
    old_password     = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password     = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        try:
            validate_password(data['new_password'])
        except Exception as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return data