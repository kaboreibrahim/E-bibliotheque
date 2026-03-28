"""
=============================================================================
 apps/users/repositories/code_repository.py
 Accès ORM pour CodeVerification
=============================================================================
"""

from django.utils import timezone
from apps.users.models.code_models import CodeVerification
from apps.users.models.user_models import User


class CodeVerificationRepository:

    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_valid_code(user: User, type_code: str, code: str) -> CodeVerification | None:
        """
        Récupère le code valide le plus récent pour un utilisateur et un type donnés.
        Valide = non utilisé, non expiré, tentatives < max.
        """
        return (
            CodeVerification.objects
            .filter(
                user=user,
                type_code=type_code,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def get_latest_pending(user: User, type_code: str) -> CodeVerification | None:
        """Récupère le dernier code non utilisé d'un type donné pour un user."""
        return (
            CodeVerification.objects
            .filter(user=user, type_code=type_code, is_used=False)
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def count_recent_attempts(user: User, type_code: str, minutes: int = 10) -> int:
        """Compte les tentatives récentes pour limiter le bruteforce."""
        from datetime import timedelta
        depuis = timezone.now() - timedelta(minutes=minutes)
        return CodeVerification.objects.filter(
            user=user,
            type_code=type_code,
            created_at__gte=depuis,
        ).count()

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create(
        user: User,
        type_code: str,
        email: str = None,
        validity_seconds: int = 180
    ) -> CodeVerification:
        """
        Crée un nouveau code OTP.
        Invalide automatiquement les anciens codes du même type.
        """
        return CodeVerification.create_verification_code(
            user=user,
            type_code=type_code,
            email=email,
            validity_seconds=validity_seconds,
        )

    @staticmethod
    def mark_as_used(code_obj: CodeVerification) -> None:
        code_obj.mark_as_used()

    @staticmethod
    def increment_attempts(code_obj: CodeVerification) -> bool:
        """Retourne True si le max de tentatives est atteint."""
        return code_obj.increment_attempts()

    @staticmethod
    def invalidate_all(user: User, type_code: str) -> int:
        """Invalide tous les codes non utilisés d'un type pour un user."""
        return CodeVerification.objects.filter(
            user=user,
            type_code=type_code,
            is_used=False
        ).update(is_used=True)