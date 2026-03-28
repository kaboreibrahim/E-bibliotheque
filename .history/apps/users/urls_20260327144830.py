"""
apps/users/urls.py
Routes separees par role pour l'authentification et la gestion des utilisateurs.
"""

from django.urls import path

from apps.users.views.auth_views import (
    LoginView,
    LogoutView,
    OTPSendView,
    OTPVerifyView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshView,
    TOTPConfirmView,
    TOTPSetupView,
    TOTPVerifyView,
)
from apps.users.views.bibliothecaire_auth_views import (
    BibliothecaireLoginView,
    BibliothecaireTOTPConfirmView,
    BibliothecaireTOTPSetupView,
    BibliothecaireTOTPVerifyView,
)
from apps.users.views.bibliothecaire_views import (
    BibliothecaireActivateView,
    BibliothecaireChangePasswordView,
    BibliothecaireCreateView,
    BibliothecaireDeactivateView,
    BibliothecaireDeleteView,
    BibliothecaireDetailView,
    BibliothecaireListView,
    BibliothecaireMeView,
    BibliothecaireUpdateView,
)
from apps.users.views.etudiant_auth_views import (
    EtudiantLoginView,
    EtudiantTOTPConfirmView,
    EtudiantTOTPSetupView,
    EtudiantTOTPVerifyView,
)
from apps.users.views.etudiant_views import (
    EtudiantActivateView,
    EtudiantChangePasswordView,
    EtudiantCreateView,
    EtudiantDeactivateView,
    EtudiantDeleteView,
    EtudiantDetailView,
    EtudiantListView,
    EtudiantMeView,
    EtudiantUpdateView,
)
from apps.users.views.user_views import (
    ChangePasswordView,
    MeView,
    UserActivateView,
    UserCreateView,
    UserDeactivateView,
    UserDeleteView,
    UserDetailView,
    UserListCreateView,
    UserListView,
    UserRetrieveView,
    UserUpdateView,
)


common_auth_urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/totp/setup/", TOTPSetupView.as_view(), name="auth-totp-setup"),
    path("auth/totp/confirm/", TOTPConfirmView.as_view(), name="auth-totp-confirm"),
    path("auth/totp/verify/", TOTPVerifyView.as_view(), name="auth-totp-verify"),
    path("auth/otp/send/", OTPSendView.as_view(), name="auth-otp-send"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="auth-otp-verify"),
    path(
        "auth/password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]


etudiant_auth_urlpatterns = [
    path("auth/etudiant/login/", EtudiantLoginView.as_view(), name="student-auth-login"),
    path("auth/etudiant/totp/setup/", EtudiantTOTPSetupView.as_view(), name="student-auth-totp-setup"),
    path("auth/etudiant/totp/confirm/", EtudiantTOTPConfirmView.as_view(), name="student-auth-totp-confirm"),
    path("auth/etudiant/totp/verify/", EtudiantTOTPVerifyView.as_view(), name="student-auth-totp-verify"),
]


bibliothecaire_auth_urlpatterns = [
    path(
        "auth/bibliothecaire/login/",
        BibliothecaireLoginView.as_view(),
        name="bibliothecaire-auth-login",
    ),
    path(
        "auth/bibliothecaire/totp/setup/",
        BibliothecaireTOTPSetupView.as_view(),
        name="bibliothecaire-auth-totp-setup",
    ),
    path(
        "auth/bibliothecaire/totp/confirm/",
        BibliothecaireTOTPConfirmView.as_view(),
        name="bibliothecaire-auth-totp-confirm",
    ),
    path(
        "auth/bibliothecaire/totp/verify/",
        BibliothecaireTOTPVerifyView.as_view(),
        name="bibliothecaire-auth-totp-verify",
    ),
]


common_user_urlpatterns = [
    path("list/utilisateur/", UserListView.as_view(), name="user-list"),
    path("creer/utilisateur/", UserCreateView.as_view(), name="user-create"),
    path("detail/utilisateur/<uuid:user_id>/", UserRetrieveView.as_view(), name="user-detail"),
    path("modifier/utilisateur/<uuid:user_id>/", UserUpdateView.as_view(), name="user-update"),
    path("supprimer/utilisateur/<uuid:user_id>/", UserDeleteView.as_view(), name="user-delete"),
    path("activer/utilisateur/<uuid:user_id>/", UserActivateView.as_view(), name="user-activate"),
    path(
        "desactiver/utilisateur/<uuid:user_id>/",
        UserDeactivateView.as_view(),
        name="user-deactivate",
    ),
    path("profil/me/", MeView.as_view(), name="user-me"),
    path("profil/me/mot-de-passe/", ChangePasswordView.as_view(), name="user-change-password"),
]


etudiant_urlpatterns = [
    path("etudiant/list/", EtudiantListView.as_view(), name="student-list"),
    path("etudiant/creer/", EtudiantCreateView.as_view(), name="student-create"),
    path("etudiant/detail/<uuid:user_id>/", EtudiantDetailView.as_view(), name="student-detail"),
    path("etudiant/modifier/<uuid:user_id>/", EtudiantUpdateView.as_view(), name="student-update"),
    path("etudiant/supprimer/<uuid:user_id>/", EtudiantDeleteView.as_view(), name="student-delete"),
    path("etudiant/activer/<uuid:user_id>/", EtudiantActivateView.as_view(), name="student-activate"),
    path(
        "etudiant/desactiver/<uuid:user_id>/",
        EtudiantDeactivateView.as_view(),
        name="student-deactivate",
    ),
    path("etudiant/profil/me/", EtudiantMeView.as_view(), name="student-me"),
    path(
        "etudiant/profil/me/mot-de-passe/",
        EtudiantChangePasswordView.as_view(),
        name="student-change-password",
    ),
]


bibliothecaire_urlpatterns = [
    path("bibliothecaire/list/", BibliothecaireListView.as_view(), name="bibliothecaire-list"),
    path("bibliothecaire/creer/", BibliothecaireCreateView.as_view(), name="bibliothecaire-create"),
    path(
        "bibliothecaire/detail/<uuid:user_id>/",
        BibliothecaireDetailView.as_view(),
        name="bibliothecaire-detail",
    ),
    path(
        "bibliothecaire/modifier/<uuid:user_id>/",
        BibliothecaireUpdateView.as_view(),
        name="bibliothecaire-update",
    ),
    path(
        "bibliothecaire/supprimer/<uuid:user_id>/",
        BibliothecaireDeleteView.as_view(),
        name="bibliothecaire-delete",
    ),
    path(
        "bibliothecaire/activer/<uuid:user_id>/",
        BibliothecaireActivateView.as_view(),
        name="bibliothecaire-activate",
    ),
    path(
        "bibliothecaire/desactiver/<uuid:user_id>/",
        BibliothecaireDeactivateView.as_view(),
        name="bibliothecaire-deactivate",
    ),
    path(
        "bibliothecaire/profil/me/",
        BibliothecaireMeView.as_view(),
        name="bibliothecaire-me",
    ),
    path(
        "bibliothecaire/profil/me/mot-de-passe/",
        BibliothecaireChangePasswordView.as_view(),
        name="bibliothecaire-change-password",
    ),
]


compatibility_user_urlpatterns = [
    path("list/etudiant/", EtudiantListView.as_view(), name="legacy-student-list"),
    path("creer/etudiant/", EtudiantCreateView.as_view(), name="legacy-student-create"),
    path("detail/etudiant/<uuid:user_id>/", EtudiantDetailView.as_view(), name="legacy-student-detail"),
    path("modifier/etudiant/<uuid:user_id>/", EtudiantUpdateView.as_view(), name="legacy-student-update"),
    path("supprimer/etudiant/<uuid:user_id>/", EtudiantDeleteView.as_view(), name="legacy-student-delete"),
    path("activer/etudiant/<uuid:user_id>/", EtudiantActivateView.as_view(), name="legacy-student-activate"),
    path(
        "desactiver/etudiant/<uuid:user_id>/",
        EtudiantDeactivateView.as_view(),
        name="legacy-student-deactivate",
    ),
    path("list/bibliothecaire/", BibliothecaireListView.as_view(), name="legacy-bibliothecaire-list"),
    path("creer/bibliothecaire/", BibliothecaireCreateView.as_view(), name="legacy-bibliothecaire-create"),
    path(
        "detail/bibliothecaire/<uuid:user_id>/",
        BibliothecaireDetailView.as_view(),
        name="legacy-bibliothecaire-detail",
    ),
    path(
        "modifier/bibliothecaire/<uuid:user_id>/",
        BibliothecaireUpdateView.as_view(),
        name="legacy-bibliothecaire-update",
    ),
    path(
        "supprimer/bibliothecaire/<uuid:user_id>/",
        BibliothecaireDeleteView.as_view(),
        name="legacy-bibliothecaire-delete",
    ),
    path(
        "activer/bibliothecaire/<uuid:user_id>/",
        BibliothecaireActivateView.as_view(),
        name="legacy-bibliothecaire-activate",
    ),
    path(
        "desactiver/bibliothecaire/<uuid:user_id>/",
        BibliothecaireDeactivateView.as_view(),
        name="legacy-bibliothecaire-deactivate",
    ),
]


# legacy_auth_urlpatterns = [
#     path("login/", LoginView.as_view(), name="legacy-auth-login"),
#     path("logout/", LogoutView.as_view(), name="legacy-auth-logout"),
#     path("token/refresh/", TokenRefreshView.as_view(), name="legacy-auth-token-refresh"),
#     path("totp/setup/", TOTPSetupView.as_view(), name="legacy-auth-totp-setup"),
#     path("totp/confirm/", TOTPConfirmView.as_view(), name="legacy-auth-totp-confirm"),
#     path("totp/verify/", TOTPVerifyView.as_view(), name="legacy-auth-totp-verify"),
#     path("otp/send/", OTPSendView.as_view(), name="legacy-auth-otp-send"),
#     path("otp/verify/", OTPVerifyView.as_view(), name="legacy-auth-otp-verify"),
#     path(
#         "password/reset/request/",
#         PasswordResetRequestView.as_view(),
#         name="legacy-auth-password-reset-request",
#     ),
#     path(
#         "password/reset/confirm/",
#         PasswordResetConfirmView.as_view(),
#         name="legacy-auth-password-reset-confirm",
#     ),
# ]


legacy_user_urlpatterns = [
    path("me/", MeView.as_view(), name="legacy-user-me"),
    path("me/password/", ChangePasswordView.as_view(), name="legacy-user-change-password"),
    path("<uuid:user_id>/activate/", UserActivateView.as_view(), name="legacy-user-activate"),
    path("<uuid:user_id>/deactivate/", UserDeactivateView.as_view(), name="legacy-user-deactivate"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="legacy-user-detail"),
    path("", UserListCreateView.as_view(), name="legacy-user-list-create"),
]


urlpatterns = (
    common_auth_urlpatterns
    + etudiant_auth_urlpatterns
    + bibliothecaire_auth_urlpatterns
    + common_user_urlpatterns
    + etudiant_urlpatterns
    + bibliothecaire_urlpatterns
    + compatibility_user_urlpatterns
    + legacy_auth_urlpatterns
    + legacy_user_urlpatterns
)
