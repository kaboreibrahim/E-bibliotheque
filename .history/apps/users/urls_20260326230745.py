from django.urls import path

from apps.users.views import (
    BibliothecaireListView,
    BibliothecaireRegistrationView,
    CurrentUserView,
    CustomTokenObtainPairView,
    StudentListView,
    StudentRegistrationView,
    TokenRefreshView,
    UserListView,
)

app_name = 'users'

urlpatterns = [
    path('', UserListView.as_view(), name='list'),
    path('me/', CurrentUserView.as_view(), name='me'),
    path('etudiants/', StudentListView.as_view(), name='etudiant-list'),
    path('bibliothecaires/', BibliothecaireListView.as_view(), name='bibliothecaire-list'),
    path('auth/register/etudiant/', StudentRegistrationView.as_view(), name='register-etudiant'),
    path(
        'auth/register/bibliothecaire/',
        BibliothecaireRegistrationView.as_view(),
        name='register-bibliothecaire',
    ),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
