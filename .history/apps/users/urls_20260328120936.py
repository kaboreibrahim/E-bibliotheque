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


# ── apps/users/urls/etudiant_urls.py ─────────────────────────────────────────
 
from django.urls import path
from apps.users.views.creation_views import (
    EtudiantListView,
    EtudiantCreateView,
    EtudiantDetailView,
    EtudiantActiverView,
    BibliothecaireListView,
    BibliothecaireCreateView,
    BibliothecaireDetailView,
)



urlpatterns = [
    # ── Liste + Création ─────────────────────────────────────
    # GET  /api/etudiants/   → lister   [Admin | Biblio]
    # POST /api/etudiants/   → créer    [Admin | Biblio avec peut_gerer_utilisateurs]
    path(
        '',
        type('_View', (EtudiantListView, EtudiantCreateView), {
            'get': EtudiantListView.get,
            'post': EtudiantCreateView.post,
        }).as_view(),
        name='etudiant-list-create'
    ),
 
    # ── Détail + Modification + Suppression ──────────────────
    # GET    /api/etudiants/<id>/   → détail   [Admin | Biblio]
    # PATCH  /api/etudiants/<id>/   → modifier [Admin | Biblio]
    # DELETE /api/etudiants/<id>/   → supprimer [Admin seulement]
    path(
        '<uuid:etudiant_id>/',
        EtudiantDetailView.as_view(),
        name='etudiant-detail'
    ),
 
    # ── Activation ───────────────────────────────────────────
    # POST /api/etudiants/<id>/activer/
    # Body: {"action": "activer" | "reactiver"}
    path(
        '<uuid:etudiant_id>/activer/',
        EtudiantActiverView.as_view(),
        name='etudiant-activer'
    ),
    
] 
 
 
urlpatterns = [
    # ── Liste + Création ─────────────────────────────────────
    # GET  /api/bibliothecaires/   → lister [Admin]
    # POST /api/bibliothecaires/   → créer  [Admin]
    path(
        '',
        type('_BView', (BibliothecaireListView, BibliothecaireCreateView), {
            'get': BibliothecaireListView.get,
            'post': BibliothecaireCreateView.post,
        }).as_view(),
        name='bibliothecaire-list-create'
    ),
 
    # ── Détail + Modification + Suppression ──────────────────
    # GET    /api/bibliothecaires/<id>/   [Admin]
    # PATCH  /api/bibliothecaires/<id>/   [Admin]
    # DELETE /api/bibliothecaires/<id>/   [Admin]
    path(
        '<uuid:biblio_id>/',
        BibliothecaireDetailView.as_view(),
        name='bibliothecaire-detail'
    ),
]