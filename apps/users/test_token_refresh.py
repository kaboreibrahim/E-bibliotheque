"""Renouvellement de session : POST /api/auth/token/refresh/."""
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.users.models import User

URL = "/api/auth/token/refresh/"


class TokenRefreshTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="lecteur@test.ci", password="Password123!", first_name="Aya", last_name="Kouame",
                                             phone="+2250708000301", user_type=User.UserType.BIBLIOTHECAIRE)
        self.refresh = str(RefreshToken.for_user(self.user))

    def test_renvoie_de_nouveaux_jetons_enveloppes(self):
        res = self.client.post(URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        data = res.data["data"]
        self.assertIn("access", data)
        self.assertNotEqual(data["refresh"], self.refresh)
        # le nouveau jeton porte les memes informations qu'a la connexion
        access = AccessToken(data["access"])
        self.assertEqual(access["user_type"], "BIBLIOTHECAIRE")
        self.assertEqual(access["email"], "lecteur@test.ci")
        # le nouveau jeton d'acces est accepte par l'API
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, status.HTTP_200_OK)

    def test_ancien_refresh_revoque_apres_rotation(self):
        self.client.post(URL, {"refresh": self.refresh}, format="json")
        res = self.client.post(URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_le_nouveau_refresh_se_renouvelle_a_son_tour(self):
        first = self.client.post(URL, {"refresh": self.refresh}, format="json").data["data"]["refresh"]
        res = self.client.post(URL, {"refresh": first}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_compte_desactive_refuse(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        res = self.client.post(URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
