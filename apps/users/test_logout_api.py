from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import RefreshTokenBlacklist, User


class LogoutApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.logout_url = reverse('logout')
        self.user = User.objects.create_user(
            email='logout.user@example.com',
            password='Password123!',
            first_name='Aminata',
            last_name='Kone',
            phone='+2250700000100',
            user_type=User.UserType.ETUDIANT,
        )
        self.other_user = User.objects.create_user(
            email='logout.other@example.com',
            password='Password123!',
            first_name='Idriss',
            last_name='Traore',
            phone='+2250700000101',
            user_type=User.UserType.ETUDIANT,
        )

    def test_logout_revokes_authenticated_user_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.logout_url,
            {'refresh': str(refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Déconnexion réussie.')
        self.assertTrue(
            RefreshTokenBlacklist.objects.filter(
                user=self.user,
                token_jti=str(refresh['jti']),
            ).exists()
        )

    def test_logout_rejects_refresh_token_from_another_user(self):
        other_refresh = RefreshToken.for_user(self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.logout_url,
            {'refresh': str(other_refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], 'Token invalide ou déjà révoqué.')
        self.assertFalse(
            RefreshTokenBlacklist.objects.filter(
                token_jti=str(other_refresh['jti']),
            ).exists()
        )
