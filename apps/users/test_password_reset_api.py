"""
SEC : la réinitialisation du mot de passe exigeait seulement l'email.
POST /api/auth/password/reset/confirm/ doit désormais présenter le
`reset_token` délivré par /api/auth/otp/verify/ (type password_reset) pour
ce compte précis ; le jeton expire et ne sert qu'une fois.
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from apps.users.models import User
from apps.users.models.code_models import CodeVerification
from apps.users.services import auth_service


NEW_PASSWORD = 'NouveauPass@2026!'


class PasswordResetApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.request_url = reverse('password-reset-request')
        self.verify_url = reverse('otp-verify')
        self.confirm_url = reverse('password-reset-confirm')
        self.user = User.objects.create_user(
            email='reset.user@example.com',
            password='AncienPass@2025!',
            first_name='Aya',
            last_name='Konan',
            phone='+2250700000200',
            user_type=User.UserType.ETUDIANT,
        )
        self.other = User.objects.create_user(
            email='reset.other@example.com',
            password='AutrePass@2025!',
            first_name='Yao',
            last_name='Kouassi',
            phone='+2250700000201',
            user_type=User.UserType.ADMINISTRATEUR,
        )

    # ── Aides ────────────────────────────────────────────────────────────────
    def _request_code(self, user):
        response = self.client.post(self.request_url, {'email': user.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return (
            CodeVerification.objects.filter(user=user, type_code='password_reset', is_used=False)
            .order_by('-created_at')
            .first()
        )

    def _verify(self, user, code):
        return self.client.post(
            self.verify_url,
            {'email': user.email, 'code': code, 'type_code': 'password_reset'},
            format='json',
        )

    def _confirm(self, email, token=None):
        payload = {'email': email, 'new_password': NEW_PASSWORD, 'confirm_password': NEW_PASSWORD}
        if token is not None:
            payload['reset_token'] = token
        return self.client.post(self.confirm_url, payload, format='json')

    def _get_token(self, user):
        code_obj = self._request_code(user)
        response = self._verify(user, code_obj.code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data['data'].get('reset_token')
        self.assertTrue(token)
        return token

    def _password_unchanged(self, user, old_password):
        user.refresh_from_db()
        self.assertTrue(user.check_password(old_password))
        self.assertFalse(user.check_password(NEW_PASSWORD))

    # ── Attaque d'origine : email seul ───────────────────────────────────────
    def test_confirm_without_token_is_rejected(self):
        response = self._confirm(self.other.email)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reset_token', response.data['errors'])
        self._password_unchanged(self.other, 'AutrePass@2025!')

    def test_confirm_with_forged_token_is_rejected(self):
        response = self._confirm(self.other.email, token='jeton-invente')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._password_unchanged(self.other, 'AutrePass@2025!')

    # ── Parcours nominal ─────────────────────────────────────────────────────
    def test_full_flow_resets_password(self):
        token = self._get_token(self.user)

        response = self._confirm(self.user.email, token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_otp_for_other_types_returns_no_reset_token(self):
        code_obj = CodeVerification.create_verification_code(self.user, 'activation')
        response = self.client.post(
            self.verify_url,
            {'email': self.user.email, 'code': code_obj.code, 'type_code': 'activation'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('reset_token', response.data['data'])

    # ── Propriétés du jeton ──────────────────────────────────────────────────
    def test_token_is_single_use(self):
        token = self._get_token(self.user)
        self.assertEqual(self._confirm(self.user.email, token).status_code, status.HTTP_200_OK)

        replay = self.client.post(
            self.confirm_url,
            {'email': self.user.email, 'reset_token': token,
             'new_password': 'EncoreUn@2026!', 'confirm_password': 'EncoreUn@2026!'},
            format='json',
        )

        self.assertEqual(replay.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_token_of_one_account_cannot_reset_another(self):
        token = self._get_token(self.user)

        response = self._confirm(self.other.email, token)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._password_unchanged(self.other, 'AutrePass@2025!')

    def test_expired_token_is_rejected(self):
        token = self._get_token(self.user)

        with patch.object(auth_service, 'PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS', -1):
            response = self._confirm(self.user.email, token)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self._password_unchanged(self.user, 'AncienPass@2025!')

    def test_unknown_email_gets_same_generic_error(self):
        response = self._confirm('inconnu@example.com', token='x')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reset_token', response.data['errors'])

    # ── Protection du code OTP lui-même ──────────────────────────────────────
    def test_otp_locked_after_max_attempts(self):
        code_obj = self._request_code(self.user)
        wrong = '000000' if code_obj.code != '000000' else '111111'

        for _ in range(code_obj.max_attempts):
            self.assertEqual(self._verify(self.user, wrong).status_code, status.HTTP_400_BAD_REQUEST)

        # Le bon code ne passe plus une fois le plafond de tentatives atteint
        response = self._verify(self.user, code_obj.code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_otp_is_rejected(self):
        code_obj = self._request_code(self.user)
        CodeVerification.objects.filter(pk=code_obj.pk).update(expires_at=code_obj.created_at - timedelta(seconds=1))

        response = self._verify(self.user, code_obj.code)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_verify_is_rate_limited(self):
        patcher = patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'login': '3/min', 'totp': '3/min'})
        patcher.start()
        self.addCleanup(patcher.stop)

        statuses = [self._verify(self.user, '123456').status_code for _ in range(4)]

        self.assertEqual(statuses[3], status.HTTP_429_TOO_MANY_REQUESTS)
