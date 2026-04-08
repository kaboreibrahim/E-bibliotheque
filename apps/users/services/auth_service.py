"""
=============================================================================
 apps/users/services/auth_service.py
 Logique métier — 3 flux de connexion distincts :
   - Étudiant       : matricule + password → TOTP Google Authenticator
   - Bibliothécaire : email    + password → TOTP Google Authenticator
   - Admin          : email    + password → TOTP Google Authenticator
=============================================================================
"""

import base64
import logging
from dataclasses import dataclass, field
from io import BytesIO

import pyotp

from django.core import signing
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models.user_models import User
from apps.users.repositories.user_repository import UserRepository, TokenBlacklistRepository
from apps.users.repositories.code_repository import CodeVerificationRepository
from apps.history.models import HistoriqueActionService as HAS

logger = logging.getLogger(__name__)

TOTP_ISSUER_NAME = "Bibliothèque Universitaire CI"
TOTP_SETUP_TOKEN_SALT = "users.totp.setup"
TOTP_SETUP_TOKEN_MAX_AGE_SECONDS = 900


@dataclass
class AuthResult:
    success:     bool
    message:     str
    data:        dict = field(default_factory=dict)
    errors:      dict = field(default_factory=dict)
    http_status: int  = 200


# =============================================================================
# 🎓  ÉTUDIANT — matricule + password + TOTP
# =============================================================================

class EtudiantAuthService:
    """
    Authentification spécifique aux étudiants.
    Flux : matricule + password → TOTP Google Authenticator → JWT tokens
    """

    @staticmethod
    def login(matricule: str, password: str, ip: str = None, ua: str = None) -> AuthResult:
        """
        Étape 1 — Vérification matricule + mot de passe.

        Retourne :
          - requires_totp: True  → l'étudiant doit valider son TOTP
          - user_id              → à passer à l'étape 2
        """
        # Rechercher l'étudiant via son matricule (dans le profil Etudiant)
        from apps.users.models.etudiant_models import Etudiant
        try:
            etudiant = Etudiant.objects.select_related('user').get(matricule=matricule)
            user     = etudiant.user
        except Etudiant.DoesNotExist:
            HAS.log_connexion(user=None, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Matricule ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        # Vérifier le mot de passe
        if not user.check_password(password):
            HAS.log_connexion(user=user, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Matricule ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        # Vérifier que le compte est actif
        if not user.is_active:
            return AuthResult(
                success=False,
                message="Votre compte est désactivé. Contactez la bibliothèque.",
                errors={'non_field_errors': ['Compte inactif.']},
                http_status=403
            )

        # Vérifier expiration du compte étudiant
        if etudiant.est_expire:
            return AuthResult(
                success=False,
                message=(
                    f"Votre compte a expiré il y a {abs(etudiant.jours_restants)} jours. "
                    f"Veuillez contacter la bibliothèque pour une réactivation."
                ),
                errors={'compte': ['Compte expiré.']},
                http_status=403
            )

        # Vérifier TOTP configuré
        if not user.totp_secret or not user.is_2fa_enabled:
            return CommonAuthService.begin_first_login_totp_setup(
                user=user,
                ip=ip,
                ua=ua,
            )

        # ✅ Étape 1 OK → demander le TOTP
        HAS.log(
            action=HAS.ACTIONS.CONNEXION_ETAPE_1,
            user=user,
            statut='succes',
            ip_address=ip,
            details={'etape': '1/2 — en attente TOTP', 'matricule': matricule}
        )

        return AuthResult(
            success=True,
            message="Identifiants valides. Veuillez saisir votre code Google Authenticator.",
            data={
                'requires_totp': True,
                'user_id':       str(user.id),
                'user_type':     'ETUDIANT',
                'nom_complet':   user.get_full_name(),
            },
            http_status=200
        )

    @staticmethod
    def verify_totp(user_id: str, totp_code: str, ip: str = None) -> AuthResult:
        """
        Étape 2 — Validation du code Google Authenticator.
        Retourne les tokens JWT si le code est correct.
        """
        user = UserRepository.get_by_id(user_id)
        if not user or user.user_type != 'ETUDIANT':
            return AuthResult(
                success=False,
                message="Étudiant introuvable.",
                http_status=404
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            HAS.log_totp(user=user, statut='echec', ip=ip)
            return AuthResult(
                success=False,
                message="Code Google Authenticator invalide ou expiré. Réessayez.",
                errors={'totp_code': ['Code TOTP incorrect.']},
                http_status=400
            )

        # ✅ TOTP valide
        UserRepository.update_totp_verified_at(user)
        tokens = _generate_tokens(user)
        HAS.log_connexion(user=user, statut='succes', ip=ip)

        return AuthResult(
            success=True,
            message="Connexion réussie. Bienvenue !",
            data=_build_successful_auth_payload(user, tokens),
            http_status=200
        )


# =============================================================================
# 📖  BIBLIOTHÉCAIRE — email + password + TOTP
# =============================================================================

class BibliothecaireAuthService:
    """
    Authentification spécifique aux bibliothécaires.
    Flux : email + password → TOTP → JWT tokens
    """

    @staticmethod
    def login(email: str, password: str, ip: str = None, ua: str = None) -> AuthResult:
        """Étape 1 — email + mot de passe."""
        user = UserRepository.get_by_email(email)

        if not user or user.user_type != 'BIBLIOTHECAIRE':
            HAS.log_connexion(user=None, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Email ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        if not user.check_password(password):
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
                message="Votre compte est désactivé. Contactez l'administrateur.",
                http_status=403
            )

        if not user.totp_secret or not user.is_2fa_enabled:
            return CommonAuthService.begin_first_login_totp_setup(
                user=user,
                ip=ip,
                ua=ua,
            )

        HAS.log(
            action=HAS.ACTIONS.CONNEXION_ETAPE_1, user=user, statut='succes',
            ip_address=ip, details={'etape': '1/2 — en attente TOTP'}
        )

        return AuthResult(
            success=True,
            message="Identifiants valides. Veuillez saisir votre code Google Authenticator.",
            data={
                'requires_totp': True,
                'user_id':       str(user.id),
                'user_type':     'BIBLIOTHECAIRE',
                'nom_complet':   user.get_full_name(),
            },
            http_status=200
        )

    @staticmethod
    def verify_totp(user_id: str, totp_code: str, ip: str = None) -> AuthResult:
        """Étape 2 — TOTP → tokens JWT."""
        user = UserRepository.get_by_id(user_id)
        if not user or user.user_type != 'BIBLIOTHECAIRE':
            return AuthResult(success=False, message="Bibliothécaire introuvable.", http_status=404)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            HAS.log_totp(user=user, statut='echec', ip=ip)
            return AuthResult(
                success=False,
                message="Code Google Authenticator invalide ou expiré.",
                errors={'totp_code': ['Code TOTP incorrect.']},
                http_status=400
            )

        UserRepository.update_totp_verified_at(user)
        tokens = _generate_tokens(user)
        HAS.log_connexion(user=user, statut='succes', ip=ip)

        return AuthResult(
            success=True,
            message="Connexion réussie.",
            data=_build_successful_auth_payload(user, tokens),
            http_status=200
        )


# =============================================================================
# 🔑  ADMINISTRATEUR — email + password + TOTP
# =============================================================================

class AdminAuthService:
    """
    Authentification spécifique aux administrateurs.
    Flux : email + password → TOTP → JWT tokens
    """

    @staticmethod
    def login(email: str, password: str, ip: str = None, ua: str = None) -> AuthResult:
        """Étape 1 — email + mot de passe."""
        user = UserRepository.get_by_email(email)

        if not user or user.user_type != 'ADMINISTRATEUR':
            HAS.log_connexion(user=None, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Email ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        if not user.check_password(password):
            HAS.log_connexion(user=user, statut='echec', ip=ip, ua=ua)
            return AuthResult(
                success=False,
                message="Email ou mot de passe incorrect.",
                errors={'non_field_errors': ['Identifiants invalides.']},
                http_status=401
            )

        if not user.is_active:
            return AuthResult(success=False, message="Compte désactivé.", http_status=403)

        if not user.totp_secret or not user.is_2fa_enabled:
            return CommonAuthService.begin_first_login_totp_setup(
                user=user,
                ip=ip,
                ua=ua,
            )

        HAS.log(
            action=HAS.ACTIONS.CONNEXION_ETAPE_1, user=user, statut='succes',
            ip_address=ip, details={'etape': '1/2 — en attente TOTP'}
        )

        return AuthResult(
            success=True,
            message="Identifiants valides. Veuillez saisir votre code Google Authenticator.",
            data={
                'requires_totp': True,
                'user_id':       str(user.id),
                'user_type':     'ADMINISTRATEUR',
                'nom_complet':   user.get_full_name(),
            },
            http_status=200
        )

    @staticmethod
    def verify_totp(user_id: str, totp_code: str, ip: str = None) -> AuthResult:
        """Étape 2 — TOTP → tokens JWT."""
        user = UserRepository.get_by_id(user_id)
        if not user or user.user_type != 'ADMINISTRATEUR':
            return AuthResult(success=False, message="Administrateur introuvable.", http_status=404)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            HAS.log_totp(user=user, statut='echec', ip=ip)
            return AuthResult(
                success=False,
                message="Code Google Authenticator invalide ou expiré.",
                errors={'totp_code': ['Code TOTP incorrect.']},
                http_status=400
            )

        UserRepository.update_totp_verified_at(user)
        tokens = _generate_tokens(user)
        HAS.log_connexion(user=user, statut='succes', ip=ip)

        return AuthResult(
            success=True,
            message="Connexion administrateur réussie.",
            data=_build_successful_auth_payload(user, tokens),
            http_status=200
        )


# =============================================================================
# 🔄  SERVICE COMMUN — Reset, OTP, Refresh, Logout, TOTP Setup
# =============================================================================

class CommonAuthService:
    """Actions communes à tous les rôles."""

    @staticmethod
    def begin_first_login_totp_setup(user: User, ip: str = None, ua: str = None) -> AuthResult:
        """Retourne les informations de configuration TOTP après validation du mot de passe."""
        setup_data = _build_login_totp_setup_payload(user)
        HAS.log(
            action=HAS.ACTIONS.CONNEXION_ETAPE_1,
            user=user,
            statut='succes',
            ip_address=ip,
            user_agent=ua,
            details={'etape': '1/2 — configuration TOTP requise'}
        )
        return AuthResult(
            success=True,
            message=(
                "Premiere connexion detectee. Scannez le QR code Google Authenticator "
                "puis confirmez votre code TOTP."
            ),
            data=setup_data,
            http_status=200
        )

    @staticmethod
    def setup_totp(user: User) -> AuthResult:
        """Génère secret + QR code URI pour configurer Google Authenticator."""
        setup_payload = _prepare_totp_setup_payload(user, regenerate_secret=True)
        return AuthResult(
            success=True,
            message="Scannez ce QR code avec Google Authenticator, puis confirmez avec /totp/confirm/.",
            data=setup_payload,
            http_status=200
        )

    @staticmethod
    def confirm_totp_setup(user: User, totp_code: str, ip: str = None) -> AuthResult:
        """Active le 2FA après confirmation du premier code TOTP."""
        if not user.totp_secret:
            return AuthResult(success=False, message="Aucun secret TOTP en attente.", http_status=400)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            HAS.log_totp(user=user, statut='echec', ip=ip)
            return AuthResult(
                success=False,
                message="Code incorrect. Réessayez avec le code actuel de Google Authenticator.",
                errors={'totp_code': ['Code invalide.']},
                http_status=400
            )

        UserRepository.set_totp_secret(user, user.totp_secret)
        UserRepository.update_totp_verified_at(user)
        HAS.log_totp(user=user, statut='succes')
        return AuthResult(
            success=True,
            message="Google Authenticator activé avec succès ! Le 2FA est maintenant actif sur votre compte.",
            http_status=200
        )

    @staticmethod
    def confirm_totp_setup_with_token(setup_token: str, totp_code: str, ip: str = None) -> AuthResult:
        """Confirme le setup TOTP sans session active après la première étape de login."""
        try:
            payload = signing.loads(
                setup_token,
                salt=TOTP_SETUP_TOKEN_SALT,
                max_age=TOTP_SETUP_TOKEN_MAX_AGE_SECONDS,
            )
        except signing.SignatureExpired:
            return AuthResult(
                success=False,
                message="La session de configuration TOTP a expire. Relancez la connexion.",
                errors={'setup_token': ['Session expiree.']},
                http_status=400,
            )
        except signing.BadSignature:
            return AuthResult(
                success=False,
                message="Jeton de configuration TOTP invalide.",
                errors={'setup_token': ['Jeton invalide.']},
                http_status=400,
            )

        if payload.get('purpose') != 'totp_setup':
            return AuthResult(
                success=False,
                message="Jeton de configuration TOTP invalide.",
                errors={'setup_token': ['Jeton invalide.']},
                http_status=400,
            )

        user = UserRepository.get_by_id(payload.get('user_id'))
        if not user:
            return AuthResult(
                success=False,
                message="Utilisateur introuvable.",
                http_status=404,
            )

        result = CommonAuthService.confirm_totp_setup(user, totp_code, ip=ip)
        if not result.success:
            return result

        tokens = _generate_tokens(user)
        HAS.log_connexion(user=user, statut='succes', ip=ip)
        return AuthResult(
            success=True,
            message="Google Authenticator active. Connexion reussie.",
            data=_build_successful_auth_payload(user, tokens),
            http_status=200,
        )

    @staticmethod
    def send_otp(user: User, type_code: str, email: str = None) -> AuthResult:
        """Envoie un code OTP par email avec anti-spam."""
        nb_recent = CodeVerificationRepository.count_recent_attempts(
            user=user, type_code=type_code, minutes=10
        )
        if nb_recent >= 3:
            return AuthResult(
                success=False,
                message="Trop de tentatives. Attendez 10 minutes avant de réessayer.",
                errors={'otp': ['Limite atteinte.']},
                http_status=429
            )

        code_obj = CodeVerificationRepository.create(
            user=user, type_code=type_code,
            email=email or user.email, validity_seconds=180
        )
        _send_otp_email(user=user, code=code_obj.code, type_code=type_code)
        HAS.log(
            action=HAS.ACTIONS.OTP_ENVOI,
            user=user,
            statut='succes',
            details={'type_otp': type_code, 'email': code_obj.email}
        )

        return AuthResult(
            success=True,
            message=f"Code OTP envoyé à {code_obj.email}. Valable 3 minutes.",
            data={'email': code_obj.email, 'expires_in_seconds': 180},
            http_status=200
        )

    @staticmethod
    def verify_otp(user: User, type_code: str, code: str, ip: str = None) -> AuthResult:
        """Vérifie un code OTP email."""
        code_obj = CodeVerificationRepository.get_valid_code(
            user=user, type_code=type_code, code=code
        )
        if not code_obj:
            pending = CodeVerificationRepository.get_latest_pending(user, type_code)
            if pending:
                CodeVerificationRepository.increment_attempts(pending)
                HAS.log(
                    action=HAS.ACTIONS.OTP_ECHEC, user=user, statut='echec',
                    ip_address=ip, details={'type_otp': type_code}
                )
            return AuthResult(
                success=False,
                message="Code OTP invalide, expiré ou nombre de tentatives dépassé.",
                errors={'code': ['Code incorrect.']},
                http_status=400
            )

        CodeVerificationRepository.mark_as_used(code_obj)
        return AuthResult(
            success=True,
            message="Code OTP vérifié avec succès.",
            data={'type_code': type_code, 'verified': True},
            http_status=200
        )

    @staticmethod
    def reset_password(email: str, new_password: str) -> AuthResult:
        """Réinitialise le mot de passe (après vérification OTP)."""
        user = UserRepository.get_by_email(email)
        if not user:
            return AuthResult(success=False, message="Compte introuvable.", http_status=404)
        UserRepository.update_password(user, new_password)
        TokenBlacklistRepository.blacklist_all_user_tokens(user)
        HAS.log_utilisateur('MODIF', auteur=user, cible_user=user, details={'action': 'reset_password'})
        return AuthResult(
            success=True,
            message="Mot de passe réinitialisé. Reconnectez-vous avec vos nouveaux identifiants.",
            http_status=200
        )

    @staticmethod
    def logout(user: User, refresh_token: str, ip: str = None) -> AuthResult:
        """Révoque le refresh token."""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            TokenBlacklistRepository.blacklist(user, str(token['jti']))
            HAS.log_deconnexion(user=user, ip=ip)
            return AuthResult(success=True, message="Déconnexion réussie.", http_status=205)
        except Exception as e:
            logger.warning(f"Logout error: {e}")
            return AuthResult(success=False, message="Token invalide ou déjà révoqué.", http_status=400)

    @staticmethod
    def refresh_token(refresh_token: str) -> AuthResult:
        """Génère un nouvel access token."""
        try:
            old_token  = RefreshToken(refresh_token)
            user       = UserRepository.get_by_id(str(old_token['user_id']))
            new_refresh = RefreshToken.for_user(user)
            old_token.blacklist()
            return AuthResult(
                success=True,
                message="Token rafraîchi.",
                data={'access': str(new_refresh.access_token), 'refresh': str(new_refresh)},
                http_status=200
            )
        except Exception as e:
            return AuthResult(
                success=False, message="Refresh token invalide ou expiré.",
                errors={'refresh': [str(e)]}, http_status=401
            )


# =============================================================================
# 🔧  HELPERS PRIVÉS
# =============================================================================

def _generate_tokens(user: User) -> dict:
    """Génère access + refresh JWT avec claims personnalisés."""
    refresh             = RefreshToken.for_user(user)
    refresh['user_type']  = user.user_type
    refresh['email']      = user.email
    refresh['first_name'] = user.first_name
    refresh['last_name']  = user.last_name
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def _generate_qr_code_base64(qr_uri: str) -> str:
    import qrcode

    image = qrcode.make(qr_uri)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f"data:image/png;base64,{encoded}"


def _prepare_totp_setup_payload(user: User, regenerate_secret: bool = False) -> dict:
    secret = user.totp_secret
    if regenerate_secret or not secret:
        secret = pyotp.random_base32()
        UserRepository.update(user, totp_secret=secret)
        user.totp_secret = secret

    qr_uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name=TOTP_ISSUER_NAME,
    )
    return {
        'totp_secret': secret,
        'qr_uri': qr_uri,
        'qr_code_base64': _generate_qr_code_base64(qr_uri),
        'instructions': [
            "1. Ouvrez Google Authenticator sur votre telephone.",
            "2. Appuyez sur '+' puis 'Scanner un QR code'.",
            "3. Scannez le QR code ou entrez le secret manuellement.",
            "4. Confirmez avec le code genere sur /api/auth/totp/confirm/.",
        ],
    }


def _generate_totp_setup_token(user: User) -> str:
    return signing.dumps(
        {'user_id': str(user.id), 'purpose': 'totp_setup'},
        salt=TOTP_SETUP_TOKEN_SALT,
    )


def _build_login_totp_setup_payload(user: User) -> dict:
    return {
        'requires_totp': False,
        'requires_totp_setup': True,
        'user_id': str(user.id),
        'user_type': user.user_type,
        'nom_complet': user.get_full_name(),
        'setup_token': _generate_totp_setup_token(user),
        'totp_setup': _prepare_totp_setup_payload(user, regenerate_secret=False),
    }


def _build_successful_auth_payload(user: User, tokens: dict) -> dict:
    data = {
        'access': tokens['access'],
        'refresh': tokens['refresh'],
        'user_id': str(user.id),
        'user_type': user.user_type,
        'email': user.email,
        'nom_complet': user.get_full_name(),
    }

    if user.user_type == 'ETUDIANT':
        profil = {}
        try:
            etu = user.profil_etudiant
            profil = {
                'matricule': etu.matricule,
                'filiere': str(etu.filiere) if etu.filiere else None,
                'niveau': str(etu.niveau) if etu.niveau else None,
                'specialite': str(etu.specialite) if etu.specialite else None,
                'jours_restants': etu.jours_restants,
                'statut_compte': etu.statut_compte,
            }
        except Exception:
            pass
        data['profil'] = profil
        return data

    if user.user_type == 'BIBLIOTHECAIRE':
        permissions = {}
        try:
            bib = user.profil_bibliothecaire
            permissions = {
                'peut_gerer_documents': bib.peut_gerer_documents,
                'peut_gerer_utilisateurs': bib.peut_gerer_utilisateurs,
                'badge_number': bib.badge_number,
            }
        except Exception:
            pass
        data['permissions'] = permissions
        return data

    data['is_superuser'] = user.is_superuser
    return data


def _send_otp_email(user: User, code: str, type_code: str) -> None:
    """Envoie le code OTP par email."""
    subjects = {
        'activation':     'Activation de votre compte — Bibliothèque Universitaire',
        'password_reset': 'Réinitialisation de votre mot de passe',
        'email_change':   "Confirmation de changement d'email",
        'code_OTP':       'Votre code de connexion',
    }
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject=subjects.get(type_code, 'Votre code OTP'),
            message=(
                f"Bonjour {user.get_full_name()},\n\n"
                f"Votre code : {code}\n\n"
                f"Ce code est valable 3 minutes. Ne le partagez avec personne.\n\n"
                f"— Bibliothèque Universitaire"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Erreur envoi OTP email à {user.email}: {e}")
