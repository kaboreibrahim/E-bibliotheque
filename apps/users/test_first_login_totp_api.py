import pyotp
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, User


class FirstLoginTotpApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.etudiant_login_url = reverse('etudiant-login')
        self.bibliothecaire_login_url = reverse('bibliothecaire-login')
        self.bibliothecaire_totp_verify_url = reverse('bibliothecaire-totp-verify')
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

    def _create_bibliothecaire_with_pending_totp(self):
        user = User.objects.create_user(
            email='biblio.pending@example.com',
            password='Password123!',
            first_name='Mariam',
            last_name='Kone',
            phone='+2250700000003',
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        user.totp_secret = pyotp.random_base32()
        user.save(update_fields=['totp_secret', 'updated_at'])

        bibliothecaire = Bibliothecaire.objects.create(
            user=user,
            badge_number='BIB-001',
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=True,
        )
        return user, bibliothecaire

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

    def test_bibliothecaire_verify_totp_activates_2fa_and_stops_returning_qr(self):
        user, bibliothecaire = self._create_bibliothecaire_with_pending_totp()

        first_login_response = self.client.post(
            self.bibliothecaire_login_url,
            {'email': user.email, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(first_login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(first_login_response.data['data']['requires_totp_setup'])
        self.assertIn('totp_setup', first_login_response.data['data'])

        verify_response = self.client.post(
            self.bibliothecaire_totp_verify_url,
            {'user_id': str(user.id), 'totp_code': pyotp.TOTP(user.totp_secret).now()},
            format='json',
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_2fa_enabled)
        self.assertIsNotNone(user.totp_verified_at)
        self.assertEqual(
            verify_response.data['data']['permissions']['badge_number'],
            bibliothecaire.badge_number,
        )

        second_login_response = self.client.post(
            self.bibliothecaire_login_url,
            {'email': user.email, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(second_login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(second_login_response.data['data']['requires_totp'])
        self.assertFalse(second_login_response.data['data'].get('requires_totp_setup', False))
        self.assertNotIn('totp_setup', second_login_response.data['data'])

    def test_bibliothecaire_login_repairs_verified_totp_state_without_qr(self):
        user, _ = self._create_bibliothecaire_with_pending_totp()
        user.totp_verified_at = timezone.now()
        user.save(update_fields=['totp_verified_at', 'updated_at'])

        response = self.client.post(
            self.bibliothecaire_login_url,
            {'email': user.email, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_2fa_enabled)
        self.assertTrue(response.data['data']['requires_totp'])
        self.assertFalse(response.data['data'].get('requires_totp_setup', False))
        self.assertNotIn('totp_setup', response.data['data'])

    def test_student_login_reports_future_start_date(self):
        user = User.objects.create_user(
            email='etu.future@example.com',
            password='Password123!',
            first_name='Nadia',
            last_name='Future',
            phone='+2250700000011',
            user_type=User.UserType.ETUDIANT,
        )
        user.totp_secret = pyotp.random_base32()
        user.save(update_fields=['totp_secret', 'updated_at'])

        debut = timezone.localdate() + timedelta(days=2)
        fin = debut + timedelta(days=10)
        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_inscription=2026,
            date_debut_validite=debut,
            date_fin_validite=fin,
            compte_active_le=timezone.now(),
        )

        response = self.client.post(
            self.etudiant_login_url,
            {'matricule': etudiant.matricule, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('sera actif a partir du', response.data['message'])

    def test_student_login_reports_expired_validity_window(self):
        user = User.objects.create_user(
            email='etu.expired@example.com',
            password='Password123!',
            first_name='Nadia',
            last_name='Expired',
            phone='+2250700000012',
            user_type=User.UserType.ETUDIANT,
        )
        user.totp_secret = pyotp.random_base32()
        user.save(update_fields=['totp_secret', 'updated_at'])

        fin = timezone.localdate() - timedelta(days=1)
        debut = fin - timedelta(days=7)
        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_inscription=2026,
            date_debut_validite=debut,
            date_fin_validite=fin,
            compte_active_le=timezone.now() - timedelta(days=10),
        )

        response = self.client.post(
            self.etudiant_login_url,
            {'matricule': etudiant.matricule, 'password': 'Password123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('expiré', response.data['message'])
        user.refresh_from_db()
        self.assertFalse(user.is_active)
