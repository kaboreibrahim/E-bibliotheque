"""
=============================================================================
 apps/users/urls.py
 Routes de l'app users — Auth + CRUD utilisateurs
=============================================================================
"""

from django.urls import path
from apps.users.views.auth_views import (
    LoginView,
    TOTPSetupView,
    TOTPConfirmView,
    TOTPVerifyView,
    OTPSendView,
    OTPVerifyView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    TokenRefreshView,
    LogoutView,
)
from apps.users.views.user_views import (
    UserListCreateView,
    UserDetailView,
    MeView,
    ChangePasswordView,
    UserActivateView,
    UserDeactivateView,
)

# ── Auth ──────────────────────────────────────────────────────────────────────
auth_urlpatterns = [
    path('login/',                    LoginView.as_view(),               name='auth-login'),
    path('logout/',                   LogoutView.as_view(),              name='auth-logout'),
    path('token/refresh/',            TokenRefreshView.as_view(),        name='auth-token-refresh'),

    # TOTP (Google Authenticator)
    path('totp/setup/',               TOTPSetupView.as_view(),           name='auth-totp-setup'),
    path('totp/confirm/',             TOTPConfirmView.as_view(),         name='auth-totp-confirm'),
    path('totp/verify/',              TOTPVerifyView.as_view(),          name='auth-totp-verify'),

    # OTP Email
    path('otp/send/',                 OTPSendView.as_view(),             name='auth-otp-send'),
    path('otp/verify/',               OTPVerifyView.as_view(),           name='auth-otp-verify'),

    # Reset password
    path('password/reset/request/',   PasswordResetRequestView.as_view(),name='auth-password-reset-request'),
    path('password/reset/confirm/',   PasswordResetConfirmView.as_view(),name='auth-password-reset-confirm'),
]

# ── Users CRUD ────────────────────────────────────────────────────────────────
user_urlpatterns = [
    path('',                          UserListCreateView.as_view(),      name='user-list-create'),
    path('me/',                       MeView.as_view(),                  name='user-me'),
    path('me/password/',              ChangePasswordView.as_view(),      name='user-change-password'),
    path('<uuid:user_id>/',           UserDetailView.as_view(),          name='user-detail'),
    path('<uuid:user_id>/activate/',  UserActivateView.as_view(),        name='user-activate'),
    path('<uuid:user_id>/deactivate/',UserDeactivateView.as_view(),      name='user-deactivate'),
]