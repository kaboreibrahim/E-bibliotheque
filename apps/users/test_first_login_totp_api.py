import pyotp
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant, User


class FirstLoginTotpApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.etudiant_login_url = reverse('etudiant-login')
        self.admin_login_url = reverse('admin-login')
        self.totp_confirm_url = reverse('totp-confirm')
        self.filiere = Filiere.objects.create(name='Droit')
        self.niveau = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M1,
        )
        self.specialite = Specialite.objects.create(
            name='Droit public',
            niveau=self.niveau,
        )

    def _create_student_with_pending_totp(self):
        user = User.objects.create_user(
            email='etu.pending@example.com',
            password='Password123!',
            first_name='Awa',
            last_name='Diallo',
            phone='+2250700000001',
            user_type=User.UserType.ETUDIANT,
        )
        user.totp_secret = pyotp.random_base32()
        user.save(update_fields=['totp_secret', 'updated_at'])

        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_inscription=2026,
        )
        return user, etudiant

    def test_student_login_returns_qr_setup_when_totp_not_enabled(self):
        user, etudiant = self._create_student_with_pending_totp()

        response = self.client.post(
            self.etudiant_login_url,
            {'matricule': etudiant.matricule, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['requires_totp_setup'])
        self.assertFalse(response.data['data']['requires_totp'])
        self.assertEqual(response.data['data']['user_id'], str(user.id))
        self.assertEqual(
            response.data['data']['totp_setup']['totp_secret'],
            user.totp_secret,
        )
        self.assertIn('otpauth://totp/', response.data['data']['totp_setup']['qr_uri'])
        self.assertTrue(
            response.data['data']['totp_setup']['qr_code_base64'].startswith(
                'data:image/png;base64,'
            )
        )
        self.assertTrue(response.data['data']['setup_token'])

    def test_first_login_setup_token_can_activate_totp_and_return_tokens(self):
        user, etudiant = self._create_student_with_pending_totp()
        login_response = self.client.post(
            self.etudiant_login_url,
            {'matricule': etudiant.matricule, 'password': 'Password123!'},
            format='json',
        )
        setup_token = login_response.data['data']['setup_token']
        totp_code = pyotp.TOTP(user.totp_secret).now()

        response = self.client.post(
            self.totp_confirm_url,
            {'setup_token': setup_token, 'totp_code': totp_code},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_2fa_enabled)
        self.assertIsNotNone(user.totp_verified_at)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['user_type'], User.UserType.ETUDIANT)
        self.assertEqual(response.data['data']['profil']['matricule'], etudiant.matricule)

    def test_admin_login_generates_qr_setup_when_secret_missing(self):
        admin = User.objects.create_superuser(
            email='admin.pending@example.com',
            password='Password123!',
            first_name='Grace',
            last_name='Hopper',
            phone='+2250700000002',
        )
        admin.totp_secret = None
        admin.is_2fa_enabled = False
        admin.save(update_fields=['totp_secret', 'is_2fa_enabled', 'updated_at'])

        response = self.client.post(
            self.admin_login_url,
            {'email': admin.email, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        admin.refresh_from_db()
        self.assertTrue(response.data['data']['requires_totp_setup'])
        self.assertEqual(response.data['data']['user_type'], User.UserType.ADMINISTRATEUR)
        self.assertEqual(
            response.data['data']['totp_setup']['totp_secret'],
            admin.totp_secret,
        )
