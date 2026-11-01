"""Photo de profil : envoi (PATCH /api/auth/profile/) et lecture par l'API (GET /api/auth/profile/avatar/)."""
import io
import shutil
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

MEDIA = Path(__file__).resolve().parent / "_test_media_avatar"


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (220, 30, 60)).save(buf, format="PNG")
    return SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")


class AvatarApiTests(APITestCase):
    def setUp(self):
        MEDIA.mkdir(exist_ok=True)
        media = override_settings(MEDIA_ROOT=str(MEDIA), DEBUG=False)
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(shutil.rmtree, MEDIA, ignore_errors=True)
        p = patch("apps.users.views.profile_views.HAS.log_utilisateur", return_value=None)
        p.start()
        self.addCleanup(p.stop)
        self.user = User.objects.create_user(email="photo@test.ci", password="Password123!", first_name="Aya", last_name="Kouame",
                                             phone="+2250708000401", user_type=User.UserType.ETUDIANT)
        self.client.force_authenticate(user=self.user)

    def test_photo_envoyee_puis_servie_par_l_api(self):
        res = self.client.patch("/api/auth/profile/", {"avatar": _png()}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertTrue(res.data["data"]["avatar_url"])
        img = self.client.get("/api/auth/profile/avatar/")
        self.assertEqual(img.status_code, status.HTTP_200_OK)
        self.assertEqual(img["Content-Type"], "image/png")
        self.assertTrue(b"".join(img.streaming_content).startswith(b"\x89PNG"))

    def test_sans_photo(self):
        self.assertEqual(self.client.get("/api/auth/profile/avatar/").status_code, status.HTTP_404_NOT_FOUND)

    def test_photo_supprimee(self):
        self.client.patch("/api/auth/profile/", {"avatar": _png()}, format="multipart")
        self.client.patch("/api/auth/profile/", {"avatar": None}, format="json")
        self.assertEqual(self.client.get("/api/auth/profile/avatar/").status_code, status.HTTP_404_NOT_FOUND)

    def test_connexion_requise(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get("/api/auth/profile/avatar/").status_code, status.HTTP_401_UNAUTHORIZED)
