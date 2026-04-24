"""
=============================================================================
 apps/users/permissions.py
 Permissions DRF personnalisées pour l'app users
=============================================================================
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


# =============================================================================
# 🔐  PERMISSIONS DE BASE
# =============================================================================

class IsAdministrateur(BasePermission):
    """Seul l'administrateur peut accéder."""
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_type == 'ADMINISTRATEUR'
        )


class IsBibliothecaire(BasePermission):
    """Seul le bibliothécaire peut accéder."""
    message = "Accès réservé aux bibliothécaires."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_type == 'BIBLIOTHECAIRE'
        )


class IsEtudiant(BasePermission):
    """Seul l'étudiant peut accéder."""
    message = "Accès réservé aux étudiants."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_type == 'ETUDIANT'
        )


class IsAdminOrBibliothecaire(BasePermission):
    """Admin ou Bibliothécaire."""
    message = "Accès réservé aux administrateurs et bibliothécaires."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_type in ('ADMINISTRATEUR', 'BIBLIOTHECAIRE')
        )


class IsOwnerOrAdmin(BasePermission):
    """
    L'utilisateur peut accéder à ses propres données.
    L'admin peut accéder à tout.
    """
    message = "Vous ne pouvez accéder qu'à vos propres données."

    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'ADMINISTRATEUR':
            return True
        # obj peut être User ou un profil lié (Etudiant, Bibliothecaire)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class IsOwnerOrAdminOrBibliothecaire(BasePermission):
    """
    Propriétaire, Admin ou Bibliothécaire.
    Utilisé pour les profils étudiants.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.user_type in ('ADMINISTRATEUR', 'BIBLIOTHECAIRE'):
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class Is2FAVerified(BasePermission):
    """
    Vérifie que le 2FA a été validé pour les rôles qui l'exigent.
    Les étudiants restent tolérés ici car leur accès est déjà filtré au login.
    """
    message = "Vous devez valider votre code Google Authenticator (2FA)."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Étudiant → déjà filtré par le flux de connexion en 2 étapes
        if request.user.user_type == 'ETUDIANT':
            return True
        # Autres rôles protégés → 2FA obligatoire
        if request.user.requires_2fa and not request.user.is_2fa_enabled:
            return False
        return True


class ReadOnly(BasePermission):
    """Autorise uniquement les méthodes de lecture (GET, HEAD, OPTIONS)."""
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
