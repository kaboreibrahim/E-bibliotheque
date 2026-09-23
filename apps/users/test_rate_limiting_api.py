"""
SEC-007 : le throttling est desactive globalement sous manage.py test
(RUNNING_TESTS dans core/settings.py, pour ne pas casser les suites qui
enchainent plusieurs connexions). Ce test verifie que le mecanisme
fonctionne reellement, en patchant directement ScopedRateThrottle.THROTTLE_RATES
(class attribute lue par DRF au moment de la requete) plutot que via
@override_settings : DRF lit ce dict une seule fois a l'import du module
(voir rest_framework/throttling.py), @override_settings sur REST_FRAMEWORK
ne le met donc pas a jour dynamiquement pour une classe deja importee.
"""
from unittest.mock import patch

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle


class LoginRateLimitingTests(APITestCase):
    def setUp(self):
        cache.clear()
        patcher = patch.object(
            ScopedRateThrottle, 'THROTTLE_RATES', {'login': '3/min', 'totp': '3/min'}
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.clear)

    def test_login_bloque_au_dela_du_seuil(self):
        payload = {'matricule': 'INEXISTANT', 'password': 'x'}

        statuses = [
            self.client.post('/api/auth/etudiant/login/', payload).status_code
            for _ in range(4)
        ]

        self.assertEqual(statuses[:3], [status.HTTP_400_BAD_REQUEST] * 3)
        self.assertEqual(statuses[3], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_reste_possible_sous_le_seuil(self):
        payload = {'matricule': 'INEXISTANT', 'password': 'x'}

        for _ in range(2):
            response = self.client.post('/api/auth/etudiant/login/', payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
