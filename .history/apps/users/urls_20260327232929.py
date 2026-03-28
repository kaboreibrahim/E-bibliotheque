"""
=============================================================================
 apps/users/urls.py
 Routes Auth — 3 flux séparés par rôle + communs

 ROUTES ÉTUDIANT   → /api/auth/etudiant/...
 ROUTES BIBLIO     → /api/auth/bibliothecaire/...
 ROUTES ADMIN      → /api/auth/admin/...
 ROUTES COMMUNES   → /api/auth/...
=============================================================================
"""

from django.urls import path
from apps.users.views.auth_views import (
    # Étudiant
    EtudiantLoginView,
    EtudiantTOTPVerifyView,
    # Bibliothécaire
    BibliothecaireLoginView,
    BibliothecaireTOTPVerifyView,
    # Admin
    AdminLoginView,
    AdminTOTPVerifyView,
    # TOTP Setup (Admin + Biblio)
    TOTPSetupView,
    TOTPConfirmView,
    # OTP Email
    OTPSendView,
    OTPVerifyView,
    # Password Reset
    PasswordResetRequestView,
    PasswordResetConfirmView,
    # Tokens
    TokenRefreshView,
    LogoutView,
    # Étudiant
    EtudiantListView,
    EtudiantCreateView,
    EtudiantDetailView,
    EtudiantActiverView,
    # Bibliothécaire
    BibliothecaireListView,
    BibliothecaireCreateView,
    BibliothecaireDetailView,
)
 

urlpatterns = [

    # ══════════════════════════════════════════════════════
    # 🎓  ÉTUDIANT — matricule + password + TOTP
    # ══════════════════════════════════════════════════════
    path(
        'etudiant/login/',
        EtudiantLoginView.as_view(),
        name='etudiant-login'
    ),
    path(
        'etudiant/totp/verify/',
        EtudiantTOTPVerifyView.as_view(),
        name='etudiant-totp-verify'
    ),

    # ══════════════════════════════════════════════════════
    # 📖  BIBLIOTHÉCAIRE — email + password + TOTP
    # ══════════════════════════════════════════════════════
    path(
        'bibliothecaire/login/',
        BibliothecaireLoginView.as_view(),
        name='bibliothecaire-login'
    ),
    path(
        'bibliothecaire/totp/verify/',
        BibliothecaireTOTPVerifyView.as_view(),
        name='bibliothecaire-totp-verify'
    ),

    # ══════════════════════════════════════════════════════
    # 🔑  ADMINISTRATEUR — email + password + TOTP
    # ══════════════════════════════════════════════════════
    path(
        'admin/login/',
        AdminLoginView.as_view(),
        name='admin-login'
    ),
    path(
        'admin/totp/verify/',
        AdminTOTPVerifyView.as_view(),
        name='admin-totp-verify'
    ),

    # ══════════════════════════════════════════════════════
    # 🔧  CONFIGURATION GOOGLE AUTHENTICATOR (Admin + Biblio)
    # ══════════════════════════════════════════════════════
    path(
        'totp/setup/',
        TOTPSetupView.as_view(),
        name='totp-setup'
    ),
    path(
        'totp/confirm/',
        TOTPConfirmView.as_view(),
        name='totp-confirm'
    ),

    # ══════════════════════════════════════════════════════
    # 📧  OTP EMAIL (commun à tous les rôles)
    # ══════════════════════════════════════════════════════
    path(
        'otp/send/',
        OTPSendView.as_view(),
        name='otp-send'
    ),
    path(
        'otp/verify/',
        OTPVerifyView.as_view(),
        name='otp-verify'
    ),

    # ══════════════════════════════════════════════════════
    # 🔄  MOT DE PASSE (commun)
    # ══════════════════════════════════════════════════════
    path(
        'password/reset/',
        PasswordResetRequestView.as_view(),
        name='password-reset-request'
    ),
    path(
        'password/reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm'
    ),

    # ══════════════════════════════════════════════════════
    # 🔑  TOKENS JWT (commun)
    # ══════════════════════════════════════════════════════
    path(
        'token/refresh/',
        TokenRefreshView.as_view(),
        name='token-refresh'
    ),
    path(
        'logout/',
        LogoutView.as_view(),
        name='logout'
    ),
]

    EtudiantListView,
    EtudiantCreateView,
    EtudiantDetailView,
    EtudiantActiverView,
    BibliothecaireListView,
    BibliothecaireCreateView,
    BibliothecaireDetailView,
)
 