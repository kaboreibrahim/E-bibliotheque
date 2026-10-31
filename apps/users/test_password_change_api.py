"""Changement du mot de passe par l'utilisateur connecte et mise a jour du telephone."""
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

URL = "/api/auth/password/change/"
PROFILE_URL = "/api/auth/profile/"


class PasswordChangeApiTests(APITestCase):
    def setUp(self):
        patcher = patch("apps.users.views.profile_views.HAS.log_utilisateur", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(
            email="lecteur@test.ci", password="Ancien@2025!", first_name="Lecteur", last_name="Test",
            phone="+2250102030400", user_type=User.UserType.ETUDIANT,
        )

    def _post(self, old, new, confirm=None, auth=True):
        if auth:
            self.client.force_authenticate(user=self.user)
        return self.client.post(URL, {"old_password": old, "new_password": new, "confirm_password": confirm or new}, format="json")

    def test_change_le_mot_de_passe(self):
        res = self._post("Ancien@2025!", "Nouveau@2026!")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Nouveau@2026!"))
        self.assertFalse(self.user.check_password("Ancien@2025!"))

    def test_ancien_mot_de_passe_incorrect(self):
        res = self._post("Mauvais@2025!", "Nouveau@2026!")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", res.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Ancien@2025!"))

    def test_confirmation_differente(self):
        res = self._post("Ancien@2025!", "Nouveau@2026!", "Autre@2026!")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", res.data["errors"])

    def test_mot_de_passe_trop_faible(self):
        res = self._post("Ancien@2025!", "12345678")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", res.data["errors"])

    def test_identique_a_l_ancien(self):
        res = self._post("Ancien@2025!", "Ancien@2025!")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_authentifie(self):
        res = self._post("Ancien@2025!", "Nouveau@2026!", auth=False)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profil_ne_change_pas_le_mot_de_passe(self):
        """L'ancien contournement (PATCH /profile/ avec old/new_password) ne doit rien modifier."""
        self.client.force_authenticate(user=self.user)
        self.client.patch(PROFILE_URL, {"old_password": "Ancien@2025!", "new_password": "Pirate@2026!", "confirm_password": "Pirate@2026!"}, format="json")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Ancien@2025!"))

    def test_mise_a_jour_du_telephone(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(PROFILE_URL, {"phone": "+225 07 08 09 10 11"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["data"]["phone"], "+2250708091011")

    def test_telephone_invalide(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(PROFILE_URL, {"phone": "abc"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_telephone_deja_utilise(self):
        User.objects.create_user(
            email="autre@test.ci", password="Autre@2025!", first_name="Autre", last_name="Compte",
            phone="+2250505050505", user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(PROFILE_URL, {"phone": "+225 05 05 05 05 05"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)

    def test_conserver_son_propre_numero(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(PROFILE_URL, {"phone": "+2250102030400"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
