"""
=============================================================================
 apps/users/views/auth_views.py
 COUCHE VUE — APIViews DRF pour l'authentification
 Flux : Request → Serializer (validation) → Service → Response
=============================================================================
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema

from apps.users.serializers.serializers import (
    LoginSerializer,
    TOTPVerifySerializer,
    TOTPConfirmSetupSerializer,
    OTPSendSerializer,
    OTPVerifySerializer,
    PasswordResetConfirmSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
)
from apps.users.services.auth_service import AuthService
from apps.users.repositories.user_repository import UserRepository


def get_client_meta(request) -> dict:
    """Extrait IP et User-Agent de la requête."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    ip  = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
    ua  = request.META.get('HTTP_USER_AGENT', '')
    return {'ip': ip, 'ua': ua}


# =============================================================================
# 🔐  CONNEXION
# =============================================================================

class LoginView(APIView):
    """
    POST /api/auth/login/

    Étape 1 — Connexion email + password.
    - Étudiant      → retourne directement les tokens JWT
    - Admin/Biblio  → retourne requires_2fa=True, user_id (puis appeler /totp/verify/)
    """
    permission_classes = [AllowAny]
    parser_classes     = [JSONParser]

    @extend_schema(tags=['Auth'], summary='Connexion', request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=400
            )

        meta   = get_client_meta(request)
        result = AuthService.login(
            email    = serializer.validated_data['email'],
            password = serializer.validated_data['password'],
            ip       = meta['ip'],
            ua       = meta['ua'],
        )

        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


# =============================================================================
# 🔑  TOTP — GOOGLE AUTHENTICATOR
# =============================================================================

class TOTPSetupView(APIView):
    """
    GET /api/auth/totp/setup/

    Génère le secret TOTP et le QR code URI pour configurer Google Authenticator.
    Réservé aux Admin et Bibliothécaires.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Auth'], summary='Setup Google Authenticator')
    def get(self, request):
        user = request.user
        if not user.requires_2fa:
            return Response(
                {'success': False, 'message': "Le 2FA TOTP est réservé aux Admin et Bibliothécaires."},
                status=403
            )
        result = AuthService.setup_totp(user)
        return Response(
            {'success': result.success, 'message': result.message, 'data': result.data},
            status=result.http_status
        )


class TOTPConfirmView(APIView):
    """
    POST /api/auth/totp/confirm/

    Confirme la configuration TOTP (premier scan QR code).
    Active définitivement le 2FA sur le compte.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Auth'], summary='Confirmer setup Google Authenticator', request=TOTPConfirmSetupSerializer)
    def post(self, request):
        serializer = TOTPConfirmSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        result = AuthService.confirm_totp_setup(
            user      = request.user,
            totp_code = serializer.validated_data['totp_code'],
        )
        return Response(
            {'success': result.success, 'message': result.message, 'errors': result.errors},
            status=result.http_status
        )


class TOTPVerifyView(APIView):
    """
    POST /api/auth/totp/verify/

    Étape 2 pour Admin/Biblio — Validation du code Google Authenticator.
    Retourne les tokens JWT si le code est correct.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Vérifier code Google Authenticator', request=TOTPVerifySerializer)
    def post(self, request):
        serializer = TOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        meta   = get_client_meta(request)
        result = AuthService.verify_totp(
            user_id   = str(serializer.validated_data['user_id']),
            totp_code = serializer.validated_data['totp_code'],
            ip        = meta['ip'],
        )
        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


# =============================================================================
# 📧  OTP EMAIL
# =============================================================================

class OTPSendView(APIView):
    """
    POST /api/auth/otp/send/

    Génère et envoie un code OTP par email.
    Utilisé pour : activation, reset password, changement email, 2FA étudiant.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Envoyer un code OTP par email', request=OTPSendSerializer)
    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        # Identifier l'utilisateur par email (passé dans le body ou connecté)
        email = serializer.validated_data.get('email') or request.data.get('user_email')
        user  = None

        if request.user.is_authenticated:
            user = request.user
        elif email:
            user = UserRepository.get_by_email(email)

        if not user:
            return Response(
                {'success': False, 'message': "Utilisateur introuvable."},
                status=404
            )

        result = AuthService.send_otp(
            user      = user,
            type_code = serializer.validated_data['type_code'],
            email     = serializer.validated_data.get('email'),
        )
        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


class OTPVerifyView(APIView):
    """
    POST /api/auth/otp/verify/

    Vérifie le code OTP reçu par email.
    - type_code = 'code_OTP' → retourne les tokens JWT (connexion étudiant 2FA)
    - autres types → confirme l'action (activation, reset, etc.)
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Vérifier un code OTP email', request=OTPVerifySerializer)
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        # Identifier l'utilisateur
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            email = request.data.get('email')
            if email:
                user = UserRepository.get_by_email(email)

        if not user:
            return Response(
                {'success': False, 'message': "Utilisateur introuvable."},
                status=404
            )

        meta   = get_client_meta(request)
        result = AuthService.verify_otp(
            user      = user,
            type_code = serializer.validated_data['type_code'],
            code      = serializer.validated_data['code'],
            ip        = meta['ip'],
        )
        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


# =============================================================================
# 🔄  RESET PASSWORD
# =============================================================================

class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password/reset/request/

    Demande de réinitialisation — envoie un OTP par email.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Demander la réinitialisation du mot de passe')
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        user  = UserRepository.get_by_email(email)

        # Réponse générique (sécurité — ne pas confirmer si l'email existe)
        if not user or not user.is_active:
            return Response({
                'success': True,
                'message': "Si un compte existe avec cet email, un code a été envoyé."
            })

        AuthService.send_otp(user=user, type_code='password_reset')
        return Response({
            'success': True,
            'message': "Si un compte existe avec cet email, un code a été envoyé."
        })


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password/reset/confirm/

    Nouveau mot de passe après vérification OTP.
    L'OTP 'password_reset' doit avoir été vérifié au préalable.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Confirmer le nouveau mot de passe', request=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        email = request.data.get('email', '').strip().lower()
        user  = UserRepository.get_by_email(email)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        result = AuthService.reset_password(
            user         = user,
            new_password = serializer.validated_data['new_password'],
        )
        return Response(
            {'success': result.success, 'message': result.message},
            status=result.http_status
        )


# =============================================================================
# 🔄  REFRESH + LOGOUT
# =============================================================================

class TokenRefreshView(APIView):
    """
    POST /api/auth/token/refresh/

    Rafraîchit l'access token depuis le refresh token.
    """
    permission_classes = [AllowAny]

    @extend_schema(tags=['Auth'], summary='Rafraîchir le token JWT', request=RefreshTokenSerializer)
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        result = AuthService.refresh_access_token(
            refresh_token=serializer.validated_data['refresh']
        )
        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Déconnexion — révoque le refresh token.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Auth'], summary='Déconnexion', request=LogoutSerializer)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        meta   = get_client_meta(request)
        result = AuthService.logout(
            user          = request.user,
            refresh_token = serializer.validated_data['refresh'],
            ip            = meta['ip'],
        )
        return Response(
            {'success': result.success, 'message': result.message},
            status=result.http_status
        )