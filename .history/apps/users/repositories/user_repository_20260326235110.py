"""
=============================================================================
 apps/users/repositories/user_repository.py

 COUCHE REPOSITORIES — Accès ORM Django uniquement.
 Aucune logique métier ici. Uniquement des requêtes en base.
=============================================================================
"""

from django.db.models import QuerySet
from apps.users.models.user_models import User, RefreshTokenBlacklist


class UserRepository:
    """
    Toutes les requêtes ORM liées au modèle User.
    Les vues et services ne touchent JAMAIS directement User.objects.
    """

    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(user_id: str) -> User | None:
        """Récupère un utilisateur par son UUID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(email: str) -> User | None:
        """Récupère un utilisateur par son email (insensible à la casse)."""
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_phone(phone: str) -> User | None:
        try:
            return User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: dict = None) -> QuerySet:
        """
        Retourne tous les utilisateurs avec filtres optionnels.
        filters ex : {'user_type': 'ETUDIANT', 'is_active': True}
        """
        qs = User.objects.all()
        if filters:
            qs = qs.filter(**filters)
        return qs.order_by('-created_at')

    @staticmethod
    def exists_by_email(email: str) -> bool:
        return User.objects.filter(email__iexact=email).exists()

    @staticmethod
    def exists_by_phone(phone: str) -> bool:
        return User.objects.filter(phone=phone).exists()

    @staticmethod
    def get_active_users_by_type(user_type: str) -> QuerySet:
        return User.objects.filter(user_type=user_type, is_active=True)

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str,
        user_type: str,
        **extra_fields
    ) -> User:
        """Crée un nouvel utilisateur via le manager custom."""
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=user_type,
            **extra_fields
        )

    @staticmethod
    def update(user: User, **fields) -> User:
        """Met à jour des champs spécifiques d'un utilisateur."""
        for key, value in fields.items():
            setattr(user, key, value)
        update_fields = list(fields.keys()) + ['updated_at']
        user.save(update_fields=update_fields)
        return user

    @staticmethod
    def update_password(user: User, new_password: str) -> None:
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])

    @staticmethod
    def activate(user: User) -> User:
        user.is_active = True
        user.save(update_fields=['is_active', 'updated_at'])
        return user

    @staticmethod
    def deactivate(user: User) -> User:
        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])
        return user

    @staticmethod
    def set_totp_secret(user: User, secret: str) -> User:
        user.totp_secret    = secret
        user.is_2fa_enabled = True
        user.save(update_fields=['totp_secret', 'is_2fa_enabled', 'updated_at'])
        return user

    @staticmethod
    def update_totp_verified_at(user: User) -> User:
        from django.utils import timezone
        user.totp_verified_at = timezone.now()
        user.save(update_fields=['totp_verified_at', 'updated_at'])
        return user

    @staticmethod
    def soft_delete(user: User) -> None:
        """Suppression logique (SafeDelete)."""
        user.delete()


# =============================================================================
# 🔑  REFRESH TOKEN BLACKLIST REPOSITORY
# =============================================================================

class TokenBlacklistRepository:

    @staticmethod
    def blacklist(user: User, token_jti: str) -> RefreshTokenBlacklist:
        """Ajoute un token à la liste noire."""
        obj, _ = RefreshTokenBlacklist.objects.get_or_create(
            token_jti=token_jti,
            defaults={'user': user}
        )
        return obj

    @staticmethod
    def is_blacklisted(token_jti: str) -> bool:
        return RefreshTokenBlacklist.objects.filter(token_jti=token_jti).exists()

    @staticmethod
    def blacklist_all_user_tokens(user: User) -> int:
        """
        Révoque tous les tokens d'un utilisateur.
        Utile pour déconnexion globale ou désactivation de compte.
        Retourne le nombre de tokens révoqués.
        """
        # SimpleJWT blacklist nativement — ceci est pour notre modèle custom
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        tokens = OutstandingToken.objects.filter(user=user)
        nb = 0
        for token in tokens:
            TokenBlacklistRepository.blacklist(user, str(token.jti))
            nb += 1
        return nb