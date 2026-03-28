"""
=============================================================================
 apps/users/services/auth_service.py

 COUCHE SERVICE — Logique métier Auth.
 Orchestration : JWT, 2FA TOTP, OTP email, activation compte.
 Ne touche pas directement aux modèles — passe par les repositories.
=============================================================================
"""

import pyotp
import logging
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models.user_models import User
from apps.users.repositories.user_repository import UserRepository, TokenBlacklistRepository
from apps.users.repositories.code_repository import CodeVerificationRepository
from apps.history.models import HistoriqueActionService as HAS

logger = logging.getLogger(__name__)


# =============================================================================
# 📦  DATA CLASSES — Résultats typés des services
# =============================================================================

@dataclass
class AuthResult:
    success:      bool
    message:      str
    data:         dict = field(default_factory=dict)
    errors:       dict = field(default_factory=dict)
    http_status:  int  = 200


# =============================================================================
# 🔐  AUTH SERVICE
# =============================================================================

class AuthService:
    """
    Gère toute la logique d'authentification :
      - Connexion (email + password)
      - JWT (access + refresh)
      - 2FA TOTP (Google Authenticator)
      - OTP email (activation, reset password, code_OTP)
      - Déconnexion (blacklist token)
    """

    # ── Connexion ─────────────────────────────────────────────────────────────

    @staticmethod
    def login(email: str, password: str, ip: str = None, ua: str = None) -> AuthResult:
        """
        Étape 1 de la connexion.

        Flux :
          1. Vérifie email + password
          2. Vérifie que le compte est actif
          3. Si Admin/Biblio → retourne requires_2fa=True (pas de token encore)
          4. Si Étudiant → retourne directement les tokens JWT
        """
        user = UserRepository.get_by_email(email)

        if not user or not user.check_password(password):
            HAS.log_connexion(user=user, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Email ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        if not user.is_active:
            return AuthResult(
                success=False,
                message="Ce compte est désactivé.",
                errors={'non_field_errors': ['Compte inactif.']},
                http_status=403
            )

        # Admin / Bibliothécaire → 2FA requis avant d'émettre le token
        if user.requires_2fa:
            HAS.log(
                action=HAS.ACTIONS.CONNEXION,
                user=user,
                statut='succes',
                ip_address=ip,
                details={'etape': '1/2 — en attente TOTP'}
            )
            return AuthResult(
                success=True,
                message="Identifiants valides. Veuillez saisir votre code Google Authenticator.",
                data={
                    'requires_2fa': True,
                    'user_id':      str(user.id),
                    'user_type':    user.user_type,
                },
                http_status=200
            )

        # Étudiant → tokens directs
        tokens = AuthService._generate_tokens(user)
        HAS.log_connexion(user=user, statut='succes', ip=ip, ua=ua)

        return AuthResult(
            success=True,
            message="Connexion réussie.",
            data={
                'access':       tokens['access'],
                'refresh':      tokens['refresh'],
                'user_type':    user.user_type,
                'user_id':      str(user.id),
                'requires_2fa': False,
            },
            http_status=200
        )

    # ── Vérification TOTP (Google Authenticator) ──────────────────────────────

    @staticmethod
    def verify_totp(user_id: str, totp_code: str, ip: str = None) -> AuthResult:
        """
        Étape 2 pour Admin/Bibliothécaire.
        Valide le code TOTP à 6 chiffres de Google Authenticator.
        """
        user = UserRepository.get_by_id(user_id)
        if not user:
            return AuthResult(
                success=False,
                message="Utilisateur introuvable.",
                http_status=404
            )

        if not user.totp_secret:
            return AuthResult(
                success=False,
                message="Google Authenticator non configuré. Contactez l'administrateur.",
                errors={'totp': ['TOTP non configuré.']},
                http_status=400
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            HAS.log_totp(user=user, statut='echec', ip=ip)
            return AuthResult(
                success=False,
                message="Code Google Authenticator invalide ou expiré.",
                errors={'totp_code': ['Code TOTP incorrect.']},
                http_status=400
            )

        # ✅ TOTP valide — émettre les tokens
        UserRepository.update_totp_verified_at(user)
        tokens = AuthService._generate_tokens(user)
        HAS.log_totp(user=user, statut='succes', ip=ip)

        return AuthResult(
            success=True,
            message="Authentification 2FA réussie.",
            data={
                'access':    tokens['access'],
                'refresh':   tokens['refresh'],
                'user_type': user.user_type,
                'user_id':   str(user.id),
            },
            http_status=200
        )

    # ── Configurer TOTP (setup Google Authenticator) ──────────────────────────

    @staticmethod
    def setup_totp(user: User) -> AuthResult:
        """
        Génère un secret TOTP et le QR code URI pour configurer Google Authenticator.
        À appeler lors du premier login Admin/Biblio.
        """
        secret   = pyotp.random_base32()
        totp     = pyotp.TOTP(secret)
        qr_uri   = totp.provisioning_uri(
            name=user.email,
            issuer_name="Bibliothèque Universitaire"
        )
        # Sauvegarder le secret (pas encore activé — l'utilisateur doit confirmer)
        UserRepository.update(user, totp_secret=secret)

        return AuthResult(
            success=True,
            message="Scannez ce QR code avec Google Authenticator.",
            data={
                'totp_secret': secret,
                'qr_uri':      qr_uri,
                'instructions': (
                    "1. Ouvrez Google Authenticator. "
                    "2. Scannez le QR code ou entrez le secret manuellement. "
                    "3. Confirmez avec le code généré."
                )
            },
            http_status=200
        )

    @staticmethod
    def confirm_totp_setup(user: User, totp_code: str) -> AuthResult:
        """
        Confirme la configuration TOTP en vérifiant le premier code.
        Active le 2FA sur le compte.
        """
        if not user.totp_secret:
            return AuthResult(
                success=False,
                message="Aucun secret TOTP en attente de confirmation.",
                http_status=400
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            return AuthResult(
                success=False,
                message="Code incorrect. Réessayez.",
                errors={'totp_code': ['Code invalide.']},
                http_status=400
            )

        UserRepository.set_totp_secret(user, user.totp_secret)
        return AuthResult(
            success=True,
            message="Google Authenticator activé avec succès. Le 2FA est maintenant obligatoire.",
            http_status=200
        )

    # ── OTP Email ─────────────────────────────────────────────────────────────

    @staticmethod
    def send_otp(user: User, type_code: str, email: str = None) -> AuthResult:
        """
        Génère et envoie un code OTP par email.
        Types : 'activation' | 'password_reset' | 'email_change' | 'code_OTP'

        Limite : max 3 codes générés en 10 minutes (anti-spam).
        """
        # Anti-spam
        nb_recent = CodeVerificationRepository.count_recent_attempts(
            user=user, type_code=type_code, minutes=10
        )
        if nb_recent >= 3:
            return AuthResult(
                success=False,
                message="Trop de tentatives. Attendez 10 minutes avant de réessayer.",
                errors={'otp': ['Limite de tentatives atteinte.']},
                http_status=429
            )

        code_obj = CodeVerificationRepository.create(
            user=user,
            type_code=type_code,
            email=email or user.email,
            validity_seconds=180  # 3 minutes
        )

        # Envoi email (adapter à votre backend email)
        AuthService._send_otp_email(user=user, code=code_obj.code, type_code=type_code)

        return AuthResult(
            success=True,
            message=f"Un code OTP a été envoyé à {code_obj.email}. Valable 3 minutes.",
            data={'email': code_obj.email, 'expires_in_seconds': 180},
            http_status=200
        )

    @staticmethod
    def verify_otp(user: User, type_code: str, code: str, ip: str = None) -> AuthResult:
        """
        Vérifie un code OTP email.
        Retourne les tokens JWT si type_code == 'code_OTP'.
        """
        code_obj = CodeVerificationRepository.get_valid_code(
            user=user, type_code=type_code, code=code
        )

        if not code_obj:
            # Vérifier si un code existe mais est expiré / dépassé
            pending = CodeVerificationRepository.get_latest_pending(user, type_code)
            if pending:
                CodeVerificationRepository.increment_attempts(pending)
                HAS.log(
                    action=HAS.ACTIONS.OTP_ECHEC,
                    user=user,
                    statut='echec',
                    ip_address=ip,
                    details={'type_otp': type_code, 'tentatives': pending.attempts}
                )
            return AuthResult(
                success=False,
                message="Code OTP invalide, expiré ou nombre de tentatives dépassé.",
                errors={'code': ['Code incorrect.']},
                http_status=400
            )

        # ✅ Code valide
        CodeVerificationRepository.mark_as_used(code_obj)

        # Si OTP 2FA étudiant → retourner les tokens
        if type_code == 'code_OTP':
            tokens = AuthService._generate_tokens(user)
            HAS.log_connexion(user=user, statut='succes', ip=ip)
            return AuthResult(
                success=True,
                message="OTP validé. Connexion réussie.",
                data={
                    'access':    tokens['access'],
                    'refresh':   tokens['refresh'],
                    'user_type': user.user_type,
                },
                http_status=200
            )

        return AuthResult(
            success=True,
            message="Code OTP vérifié avec succès.",
            data={'type_code': type_code, 'user_id': str(user.id)},
            http_status=200
        )

    # ── Reset Password ────────────────────────────────────────────────────────

    @staticmethod
    def reset_password(user: User, new_password: str) -> AuthResult:
        """
        Réinitialise le mot de passe après vérification OTP.
        Le code OTP 'password_reset' doit avoir été vérifié avant.
        """
        UserRepository.update_password(user, new_password)
        # Révoquer tous les tokens existants
        TokenBlacklistRepository.blacklist_all_user_tokens(user)

        HAS.log_utilisateur('MODIF', auteur=user, cible_user=user,
                             details={'action': 'reset_password'})

        return AuthResult(
            success=True,
            message="Mot de passe réinitialisé avec succès. Reconnectez-vous.",
            http_status=200
        )

    # ── Déconnexion ───────────────────────────────────────────────────────────

    @staticmethod
    def logout(user: User, refresh_token: str, ip: str = None) -> AuthResult:
        """
        Révoque le refresh token et l'ajoute à la blacklist.
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Aussi dans notre blacklist custom
            TokenBlacklistRepository.blacklist(user, str(token['jti']))
            HAS.log_deconnexion(user=user, ip=ip)

            return AuthResult(
                success=True,
                message="Déconnexion réussie.",
                http_status=205
            )
        except Exception as e:
            logger.warning(f"Logout error for user {user.id}: {e}")
            return AuthResult(
                success=False,
                message="Token invalide ou déjà révoqué.",
                http_status=400
            )

    # ── Refresh Token ─────────────────────────────────────────────────────────

    @staticmethod
    def refresh_access_token(refresh_token: str) -> AuthResult:
        """
        Génère un nouvel access token depuis le refresh token.
        L'ancien refresh est révoqué (rotation activée dans SimpleJWT).
        """
        try:
            token      = RefreshToken(refresh_token)
            new_access = str(token.access_token)
            # Rotation : nouveau refresh
            token.blacklist()
            new_token   = RefreshToken.for_user(
                User.objects.get(id=token['user_id'])
            )
            return AuthResult(
                success=True,
                message="Token rafraîchi avec succès.",
                data={
                    'access':  new_access,
                    'refresh': str(new_token),
                },
                http_status=200
            )
        except Exception as e:
            return AuthResult(
                success=False,
                message="Refresh token invalide ou expiré.",
                errors={'refresh': [str(e)]},
                http_status=401
            )

    # ── Helpers privés ────────────────────────────────────────────────────────

    @staticmethod
    def _generate_tokens(user: User) -> dict:
        """Génère access + refresh token pour un utilisateur."""
        refresh = RefreshToken.for_user(user)
        # Ajouter des claims personnalisés
        refresh['user_type']  = user.user_type
        refresh['email']      = user.email
        refresh['first_name'] = user.first_name
        refresh['last_name']  = user.last_name

        return {
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def _send_otp_email(user: User, code: str, type_code: str) -> None:
        """
        Envoie le code OTP par email.
        Adapter selon votre backend (SendGrid, SMTP Django, etc.)
        """
        subjects = {
            'activation':     'Activation de votre compte — Bibliothèque',
            'password_reset': 'Réinitialisation de votre mot de passe',
            'email_change':   'Confirmation de changement d\'email',
            'code_OTP':       'Votre code de connexion',
        }
        subject = subjects.get(type_code, 'Votre code OTP')
        body = (
            f"Bonjour {user.get_full_name()},\n\n"
            f"Votre code : {code}\n\n"
            f"Ce code est valable 3 minutes.\n"
            f"Ne le partagez avec personne.\n\n"
            f"— Bibliothèque Universitaire"
        )
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Erreur envoi OTP email à {user.email}: {e}")