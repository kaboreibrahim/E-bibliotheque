"""
=============================================================================
 apps/users/serializers/auth_serializers.py
 Serializers d'authentification — 3 flux séparés :
   1. Étudiant       → matricule + password + TOTP
   2. Bibliothécaire → email    + password + TOTP
   3. Admin          → email    + password + TOTP
=============================================================================
"""

import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


# =============================================================================
# 1️⃣  ÉTUDIANT — matricule + password
# =============================================================================

class EtudiantLoginSerializer(serializers.Serializer):
    """
    Étape 1 connexion étudiant.
    Données attendues :
      {
        "matricule": "ETU202512345",
        "password":  "monMotDePasse"
      }
    """
    matricule = serializers.CharField(
        max_length=20,
        help_text="Matricule de l'étudiant. Format : ETU + année + 5 chiffres. Ex: ETU202512345"
    )
    password  = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mot de passe du compte étudiant."
    )

    def validate_matricule(self, value):
        value = value.strip().upper()
        if not re.match(r'^ETU\d{9,}$', value):
            raise serializers.ValidationError(
                "Format de matricule invalide. Attendu : ETU + année + 5 chiffres. Ex: ETU202512345"
            )
        return value


class EtudiantTOTPVerifySerializer(serializers.Serializer):
    """
    Étape 2 connexion étudiant — validation Google Authenticator.
    Données attendues :
      {
        "user_id":   "uuid-de-l-etudiant",
        "totp_code": "123456"
      }
    """
    user_id   = serializers.UUIDField(
        help_text="UUID retourné à l'étape 1 de connexion."
    )
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code à 6 chiffres de Google Authenticator."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code TOTP doit contenir uniquement des chiffres.")
        return value


# =============================================================================
# 2️⃣  BIBLIOTHÉCAIRE — email + password
# =============================================================================

class BibliothecaireLoginSerializer(serializers.Serializer):
    """
    Étape 1 connexion bibliothécaire.
    Données attendues :
      {
        "email":    "biblio.kone@universite-ci.edu",
        "password": "monMotDePasse"
      }
    """
    email    = serializers.EmailField(
        help_text="Adresse email professionnelle du bibliothécaire."
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mot de passe du compte bibliothécaire."
    )

    def validate_email(self, value):
        return value.lower().strip()


class BibliothecaireTOTPVerifySerializer(serializers.Serializer):
    """
    Étape 2 connexion bibliothécaire — validation Google Authenticator.
    Données attendues :
      {
        "user_id":   "uuid-du-bibliothecaire",
        "totp_code": "654321"
      }
    """
    user_id   = serializers.UUIDField(
        help_text="UUID retourné à l'étape 1."
    )
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code à 6 chiffres Google Authenticator."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code TOTP doit contenir uniquement des chiffres.")
        return value


# =============================================================================
# 3️⃣  ADMINISTRATEUR — email + password
# =============================================================================

class AdminLoginSerializer(serializers.Serializer):
    """
    Étape 1 connexion administrateur.
    Données attendues :
      {
        "email":    "admin@universite-ci.edu",
        "password": "monMotDePasse"
      }
    """
    email    = serializers.EmailField(
        help_text="Adresse email de l'administrateur."
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mot de passe administrateur."
    )

    def validate_email(self, value):
        return value.lower().strip()


class AdminTOTPVerifySerializer(serializers.Serializer):
    """
    Étape 2 connexion admin — validation Google Authenticator.
    Données attendues :
      {
        "user_id":   "uuid-de-l-admin",
        "totp_code": "789012"
      }
    """
    user_id   = serializers.UUIDField(
        help_text="UUID retourné à l'étape 1."
    )
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code à 6 chiffres Google Authenticator."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code TOTP doit contenir uniquement des chiffres.")
        return value


# =============================================================================
# 🔄  COMMUNS — OTP, Reset Password, Refresh, Logout
# =============================================================================

class OTPSendSerializer(serializers.Serializer):
    """
    Envoi d'un code OTP par email.
    Données attendues :
      {
        "type_code": "password_reset",
        "email":     "optionnel@email.com"
      }
    """
    type_code = serializers.ChoiceField(
        choices=['activation', 'password_reset', 'email_change', 'code_OTP'],
        help_text="Type de code OTP : activation | password_reset | email_change | code_OTP"
    )
    email = serializers.EmailField(
        required=False,
        help_text="Email de destination (optionnel — utilise l'email du compte par défaut)."
    )


class OTPVerifySerializer(serializers.Serializer):
    """
    Vérification d'un code OTP email.
    Données attendues :
      {
        "code":      "123456",
        "type_code": "activation",
        "email":     "user@email.com"
      }
    """
    code      = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Code OTP à 6 chiffres reçu par email."
    )
    type_code = serializers.ChoiceField(
        choices=['activation', 'password_reset', 'email_change', 'code_OTP'],
        help_text="Type du code OTP à vérifier."
    )
    email     = serializers.EmailField(
        required=False,
        help_text="Email du compte (requis si l'utilisateur n'est pas connecté)."
    )

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code OTP doit contenir uniquement des chiffres.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Demande de réinitialisation de mot de passe.
    Données attendues :
      {
        "email": "user@universite-ci.edu"
      }
    """
    email = serializers.EmailField(help_text="Email du compte à réinitialiser.")


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Confirmation nouveau mot de passe après vérification OTP.
    Données attendues :
      {
        "email":            "user@universite-ci.edu",
        "new_password":     "NouveauMotDePasse123!",
        "confirm_password": "NouveauMotDePasse123!"
      }
    """
    email            = serializers.EmailField(help_text="Email du compte.")
    new_password     = serializers.CharField(
        write_only=True, min_length=8,
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
            raise serializers.ValidationError(
                {'confirm_password': "Les mots de passe ne correspondent pas."}
            )
        try:
            validate_password(data['new_password'])
        except Exception as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return data


class TokenRefreshSerializer(serializers.Serializer):
    """
    Rafraîchissement du token d'accès.
    Données attendues :
      {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
      }
    """
    refresh = serializers.CharField(help_text="Refresh token JWT valide.")


class LogoutSerializer(serializers.Serializer):
    """
    Déconnexion.
    Données attendues :
      {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
      }
    """
    refresh = serializers.CharField(help_text="Refresh token à révoquer.")


class TOTPSetupConfirmSerializer(serializers.Serializer):
    """
    Confirmation de la configuration TOTP (premier scan QR code).
    Données attendues :
      {
        "totp_code": "123456"
      }
    """
    totp_code = serializers.CharField(
        max_length=6, min_length=6,
        help_text="Premier code généré après scan du QR code Google Authenticator."
    )

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code TOTP invalide.")
        return value