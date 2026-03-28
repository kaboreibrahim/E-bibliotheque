"""
apps/users/urls.py
Routes classees par domaine : etudiant, bibliotheque, administration.
"""

from django.urls import path

from apps.users.views.administration_auth_views import (
    AdministrationLoginView,
    AdministrationTOTPConfirmView,
    AdministrationTOTPSetupView,
    AdministrationTOTPVerifyView,
)
from apps.users.views.administration_views import (
    AdministrationActivateView,
    AdministrationChangePasswordView,
    AdministrationCreateView,
    AdministrationDeactivateView,
    AdministrationDeleteView,
    AdministrationDetailView,
    AdministrationListView,
    AdministrationMeView,
    AdministrationUpdateView,
)
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


etudiant_urlpatterns = [
    path("etudiant/auth/login/", EtudiantLoginView.as_view(), name="student-auth-login"),
    path("etudiant/auth/totp/setup/", EtudiantTOTPSetupView.as_view(), name="student-auth-totp-setup"),
    path("etudiant/auth/totp/confirm/", EtudiantTOTPConfirmView.as_view(), name="student-auth-totp-confirm"),
    path("etudiant/auth/totp/verify/", EtudiantTOTPVerifyView.as_view(), name="student-auth-totp-verify"),
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


bibliotheque_urlpatterns = [
    path("bibliotheque/auth/login/", BibliothecaireLoginView.as_view(), name="bibliotheque-auth-login"),
    path(
        "bibliotheque/auth/totp/setup/",
        BibliothecaireTOTPSetupView.as_view(),
        name="bibliotheque-auth-totp-setup",
    ),
    path(
        "bibliotheque/auth/totp/confirm/",
        BibliothecaireTOTPConfirmView.as_view(),
        name="bibliotheque-auth-totp-confirm",
    ),
    path(
        "bibliotheque/auth/totp/verify/",
        BibliothecaireTOTPVerifyView.as_view(),
        name="bibliotheque-auth-totp-verify",
    ),
    path("bibliotheque/list/", BibliothecaireListView.as_view(), name="bibliotheque-list"),
    path("bibliotheque/creer/", BibliothecaireCreateView.as_view(), name="bibliotheque-create"),
    path(
        "bibliotheque/detail/<uuid:user_id>/",
        BibliothecaireDetailView.as_view(),
        name="bibliotheque-detail",
    ),
    path(
        "bibliotheque/modifier/<uuid:user_id>/",
        BibliothecaireUpdateView.as_view(),
        name="bibliotheque-update",
    ),
    path(
        "bibliotheque/supprimer/<uuid:user_id>/",
        BibliothecaireDeleteView.as_view(),
        name="bibliotheque-delete",
    ),
    path(
        "bibliotheque/activer/<uuid:user_id>/",
        BibliothecaireActivateView.as_view(),
        name="bibliotheque-activate",
    ),
    path(
        "bibliotheque/desactiver/<uuid:user_id>/",
        BibliothecaireDeactivateView.as_view(),
        name="bibliotheque-deactivate",
    ),
    path(
        "bibliotheque/profil/me/",
        BibliothecaireMeView.as_view(),
        name="bibliotheque-me",
    ),
    path(
        "bibliotheque/profil/me/mot-de-passe/",
        BibliothecaireChangePasswordView.as_view(),
        name="bibliotheque-change-password",
    ),
]


administration_urlpatterns = [
    path("administration/auth/login/", AdministrationLoginView.as_view(), name="administration-auth-login"),
    path(
        "administration/auth/totp/setup/",
        AdministrationTOTPSetupView.as_view(),
        name="administration-auth-totp-setup",
    ),
    path(
        "administration/auth/totp/confirm/",
        AdministrationTOTPConfirmView.as_view(),
        name="administration-auth-totp-confirm",
    ),
    path(
        "administration/auth/totp/verify/",
        AdministrationTOTPVerifyView.as_view(),
        name="administration-auth-totp-verify",
    ),
    path("administration/list/", AdministrationListView.as_view(), name="administration-list"),
    path("administration/creer/", AdministrationCreateView.as_view(), name="administration-create"),
    path(
        "administration/detail/<uuid:user_id>/",
        AdministrationDetailView.as_view(),
        name="administration-detail",
    ),
    path(
        "administration/modifier/<uuid:user_id>/",
        AdministrationUpdateView.as_view(),
        name="administration-update",
    ),
    path(
        "administration/supprimer/<uuid:user_id>/",
        AdministrationDeleteView.as_view(),
        name="administration-delete",
    ),
    path(
        "administration/activer/<uuid:user_id>/",
        AdministrationActivateView.as_view(),
        name="administration-activate",
    ),
    path(
        "administration/desactiver/<uuid:user_id>/",
        AdministrationDeactivateView.as_view(),
        name="administration-deactivate",
    ),
    path("administration/profil/me/", AdministrationMeView.as_view(), name="administration-me"),
    path(
        "administration/profil/me/mot-de-passe/",
        AdministrationChangePasswordView.as_view(),
        name="administration-change-password",
    ),
    path("administration/utilisateur/list/", UserListView.as_view(), name="user-list"),
    path("administration/utilisateur/creer/", UserCreateView.as_view(), name="user-create"),
    path(
        "administration/utilisateur/detail/<uuid:user_id>/",
        UserRetrieveView.as_view(),
        name="user-detail",
    ),
    path(
        "administration/utilisateur/modifier/<uuid:user_id>/",
        UserUpdateView.as_view(),
        name="user-update",
    ),
    path(
        "administration/utilisateur/supprimer/<uuid:user_id>/",
        UserDeleteView.as_view(),
        name="user-delete",
    ),
    path(
        "administration/utilisateur/activer/<uuid:user_id>/",
        UserActivateView.as_view(),
        name="user-activate",
    ),
    path(
        "administration/utilisateur/desactiver/<uuid:user_id>/",
        UserDeactivateView.as_view(),
        name="user-deactivate",
    ),
]


common_auth_urlpatterns = [
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


# compatibility_urlpatterns = [
#     path("auth/login/", LoginView.as_view(), name="auth-login"),
#     path("auth/etudiant/login/", EtudiantLoginView.as_view(), name="legacy-student-auth-login"),
#     path(
#         "auth/etudiant/totp/setup/",
#         EtudiantTOTPSetupView.as_view(),
#         name="legacy-student-auth-totp-setup",
#     ),
#     path(
#         "auth/etudiant/totp/confirm/",
#         EtudiantTOTPConfirmView.as_view(),
#         name="legacy-student-auth-totp-confirm",
#     ),
#     path(
#         "auth/etudiant/totp/verify/",
#         EtudiantTOTPVerifyView.as_view(),
#         name="legacy-student-auth-totp-verify",
#     ),
#     path(
#         "auth/bibliothecaire/login/",
#         BibliothecaireLoginView.as_view(),
#         name="legacy-bibliothecaire-auth-login",
#     ),
#     path(
#         "auth/bibliothecaire/totp/setup/",
#         BibliothecaireTOTPSetupView.as_view(),
#         name="legacy-bibliothecaire-auth-totp-setup",
#     ),
#     path(
#         "auth/bibliothecaire/totp/confirm/",
#         BibliothecaireTOTPConfirmView.as_view(),
#         name="legacy-bibliothecaire-auth-totp-confirm",
#     ),
#     path(
#         "auth/bibliothecaire/totp/verify/",
#         BibliothecaireTOTPVerifyView.as_view(),
#         name="legacy-bibliothecaire-auth-totp-verify",
#     ),
#     path("list/etudiant/", EtudiantListView.as_view(), name="legacy-student-list"),
#     path("creer/etudiant/", EtudiantCreateView.as_view(), name="legacy-student-create"),
#     path("detail/etudiant/<uuid:user_id>/", EtudiantDetailView.as_view(), name="legacy-student-detail"),
#     path("modifier/etudiant/<uuid:user_id>/", EtudiantUpdateView.as_view(), name="legacy-student-update"),
#     path("supprimer/etudiant/<uuid:user_id>/", EtudiantDeleteView.as_view(), name="legacy-student-delete"),
#     path("activer/etudiant/<uuid:user_id>/", EtudiantActivateView.as_view(), name="legacy-student-activate"),
#     path(
#         "desactiver/etudiant/<uuid:user_id>/",
#         EtudiantDeactivateView.as_view(),
#         name="legacy-student-deactivate",
#     ),
#     path(
#         "bibliothecaire/auth/login/",
#         BibliothecaireLoginView.as_view(),
#         name="legacy-bibliothecaire-auth-login-2",
#     ),
#     path("bibliothecaire/list/", BibliothecaireListView.as_view(), name="legacy-bibliothecaire-list-2"),
#     path("bibliothecaire/creer/", BibliothecaireCreateView.as_view(), name="legacy-bibliothecaire-create-2"),
#     path(
#         "bibliothecaire/detail/<uuid:user_id>/",
#         BibliothecaireDetailView.as_view(),
#         name="legacy-bibliothecaire-detail-2",
#     ),
#     path(
#         "bibliothecaire/modifier/<uuid:user_id>/",
#         BibliothecaireUpdateView.as_view(),
#         name="legacy-bibliothecaire-update-2",
#     ),
#     path(
#         "bibliothecaire/supprimer/<uuid:user_id>/",
#         BibliothecaireDeleteView.as_view(),
#         name="legacy-bibliothecaire-delete-2",
#     ),
#     path(
#         "bibliothecaire/activer/<uuid:user_id>/",
#         BibliothecaireActivateView.as_view(),
#         name="legacy-bibliothecaire-activate-2",
#     ),
#     path(
#         "bibliothecaire/desactiver/<uuid:user_id>/",
#         BibliothecaireDeactivateView.as_view(),
#         name="legacy-bibliothecaire-deactivate-2",
#     ),
#     path("list/bibliothecaire/", BibliothecaireListView.as_view(), name="legacy-bibliothecaire-list"),
#     path("creer/bibliothecaire/", BibliothecaireCreateView.as_view(), name="legacy-bibliothecaire-create"),
#     path(
#         "detail/bibliothecaire/<uuid:user_id>/",
#         BibliothecaireDetailView.as_view(),
#         name="legacy-bibliothecaire-detail",
#     ),
#     path(
#         "modifier/bibliothecaire/<uuid:user_id>/",
#         BibliothecaireUpdateView.as_view(),
#         name="legacy-bibliothecaire-update",
#     ),
#     path(
#         "supprimer/bibliothecaire/<uuid:user_id>/",
#         BibliothecaireDeleteView.as_view(),
#         name="legacy-bibliothecaire-delete",
#     ),
#     path(
#         "activer/bibliothecaire/<uuid:user_id>/",
#         BibliothecaireActivateView.as_view(),
#         name="legacy-bibliothecaire-activate",
#     ),
#     path(
#         "desactiver/bibliothecaire/<uuid:user_id>/",
#         BibliothecaireDeactivateView.as_view(),
#         name="legacy-bibliothecaire-deactivate",
#     ),
#     path("list/administrateur/", AdministrationListView.as_view(), name="legacy-administration-list"),
#     path("creer/administrateur/", AdministrationCreateView.as_view(), name="legacy-administration-create"),
#     path(
#         "detail/administrateur/<uuid:user_id>/",
#         AdministrationDetailView.as_view(),
#         name="legacy-administration-detail",
#     ),
#     path(
#         "modifier/administrateur/<uuid:user_id>/",
#         AdministrationUpdateView.as_view(),
#         name="legacy-administration-update",
#     ),
#     path(
#         "supprimer/administrateur/<uuid:user_id>/",
#         AdministrationDeleteView.as_view(),
#         name="legacy-administration-delete",
#     ),
#     path(
#         "activer/administrateur/<uuid:user_id>/",
#         AdministrationActivateView.as_view(),
#         name="legacy-administration-activate",
#     ),
#     path(
#         "desactiver/administrateur/<uuid:user_id>/",
#         AdministrationDeactivateView.as_view(),
#         name="legacy-administration-deactivate",
#     ),
#     path("profil/me/", MeView.as_view(), name="user-me"),
#     path("profil/me/mot-de-passe/", ChangePasswordView.as_view(), name="user-change-password"),
#     path("me/", MeView.as_view(), name="legacy-user-me"),
#     path("me/password/", ChangePasswordView.as_view(), name="legacy-user-change-password"),
#     path("<uuid:user_id>/activate/", UserActivateView.as_view(), name="legacy-user-activate"),
#     path("<uuid:user_id>/deactivate/", UserDeactivateView.as_view(), name="legacy-user-deactivate"),
#     path("<uuid:user_id>/", UserDetailView.as_view(), name="legacy-user-detail"),
#     path("", UserListCreateView.as_view(), name="legacy-user-list-create"),
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


urlpatterns = (
    etudiant_urlpatterns
    + bibliotheque_urlpatterns
    + administration_urlpatterns
    + common_auth_urlpatterns
    # + compatibility_urlpatterns
)
