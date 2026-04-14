import pyotp
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Bibliothecaire, PersonneExterne, User


class PersonneExterneApiTests(APITestCase):
    def setUp(self):
        self.login_url = reverse('personne-externe-login')
        self.totp_verify_url = reverse('personne-externe-totp-verify')
        self.totp_confirm_url = reverse('totp-confirm')
        self.profile_url = reverse('current-user-profile')
        self.create_url = reverse('personnes-externes:personne-externe-list-create')
        self.admin = User.objects.create_superuser(
            email='admin-personne@example.com',
            password='Password123!',
            first_name='Admin',
            last_name='Personne',
            phone='+2250102030500',
        )
        self.biblio = User.objects.create_user(
            email='biblio-personne@example.com',
            password='Password123!',
            first_name='Biblio',
            last_name='Personne',
            phone='+2250102030501',
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(
            user=self.biblio,
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=True,
        )

    def test_admin_can_create_personne_externe(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.create_url,
            {
                'first_name': 'Awa',
                'last_name': 'Konan',
                'email': 'awa.externe@example.com',
                'phone': '+2250700000200',
                'password': 'Externe@2025!',
                'confirm_password': 'Externe@2025!',
                'numero_piece': 'CNI-12345',
                'profession': 'Juriste',
                'lieu_habitation': 'Yopougon',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['user_type'], User.UserType.PERSONNE_EXTERNE)
        personne = PersonneExterne.objects.select_related('user').get(
            user__email='awa.externe@example.com'
        )
        self.assertEqual(personne.numero_piece, 'CNI-12345')
        self.assertEqual(personne.profession, 'Juriste')
        self.assertEqual(personne.lieu_habitation, 'Yopougon')

    def _create_personne_externe_user(self, email, phone):
        user = User.objects.create_user(
            email=email,
            password='Externe@2025!',
            first_name='Externe',
            last_name='Login',
            phone=phone,
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        personne = PersonneExterne.objects.create(
            user=user,
            numero_piece='PP-556677',
            profession='Consultant',
            lieu_habitation='Cocody',
        )
        return user, personne

    def test_personne_externe_first_login_returns_qr_setup_when_totp_not_enabled(self):
        user, _ = self._create_personne_externe_user(
            email='externe.login@example.com',
            phone='+2250700000201',
        )

        response = self.client.post(
            self.login_url,
            {'email': user.email, 'password': 'Externe@2025!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['requires_totp_setup'])
        self.assertFalse(response.data['data']['requires_totp'])
        self.assertEqual(response.data['data']['user_type'], User.UserType.PERSONNE_EXTERNE)
        self.assertTrue(response.data['data']['setup_token'])
        self.assertIn('totp_setup', response.data['data'])
        user.refresh_from_db()
        self.assertEqual(
            response.data['data']['totp_setup']['totp_secret'],
            user.totp_secret,
        )

    def test_personne_externe_first_login_setup_token_can_activate_totp_and_return_tokens(self):
        user, personne = self._create_personne_externe_user(
            email='externe.setup@example.com',
            phone='+2250700000203',
        )

        login_response = self.client.post(
            self.login_url,
            {'email': user.email, 'password': 'Externe@2025!'},
            format='json',
        )
        user.refresh_from_db()
        totp_code = pyotp.TOTP(user.totp_secret).now()

        response = self.client.post(
            self.totp_confirm_url,
            {'setup_token': login_response.data['data']['setup_token'], 'totp_code': totp_code},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_2fa_enabled)
        self.assertIsNotNone(user.totp_verified_at)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(
            response.data['data']['profil']['personne_externe_id'],
            str(personne.id),
        )

    def test_personne_externe_login_requires_totp_then_verify_returns_tokens(self):
        user, personne = self._create_personne_externe_user(
            email='externe.verify@example.com',
            phone='+2250700000204',
        )
        user.totp_secret = pyotp.random_base32()
        user.is_2fa_enabled = True
        user.save(update_fields=['totp_secret', 'is_2fa_enabled', 'updated_at'])

        login_response = self.client.post(
            self.login_url,
            {'email': user.email, 'password': 'Externe@2025!'},
            format='json',
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(login_response.data['data']['requires_totp'])
        self.assertEqual(login_response.data['data']['user_id'], str(user.id))

        response = self.client.post(
            self.totp_verify_url,
            {'user_id': str(user.id), 'totp_code': pyotp.TOTP(user.totp_secret).now()},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['user_type'], User.UserType.PERSONNE_EXTERNE)
        self.assertEqual(
            response.data['data']['profil']['personne_externe_id'],
            str(personne.id),
        )
        self.assertEqual(response.data['data']['profil']['numero_piece'], 'PP-556677')

    def test_personne_externe_profile_is_returned(self):
        user = User.objects.create_user(
            email='externe.profile@example.com',
            password='Externe@2025!',
            first_name='Externe',
            last_name='Profile',
            phone='+2250700000202',
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        personne = PersonneExterne.objects.create(
            user=user,
            numero_piece='CNI-778899',
            profession='Enseignant',
            lieu_habitation='Bouake',
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], User.UserType.PERSONNE_EXTERNE)
        self.assertEqual(
            response.data['data']['profil']['personne_externe_id'],
            str(personne.id),
        )
        self.assertEqual(response.data['data']['profil']['profession'], 'Enseignant')
