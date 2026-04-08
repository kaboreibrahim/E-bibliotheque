import os
import shutil

from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, User


TEST_MEDIA_ROOT = os.path.join(
    os.path.dirname(__file__),
    '_test_media_profile',
)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CurrentUserProfileApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.url = reverse('current-user-profile')
        self.filiere = Filiere.objects.create(name='Informatique')
        self.niveau = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M1,
        )
        self.specialite = Specialite.objects.create(
            name='Reseaux',
            niveau=self.niveau,
        )

    def _create_etudiant(self):
        user = User.objects.create_user(
            email='etu@example.com',
            password='Password123!',
            first_name='Awa',
            last_name='Traore',
            phone='+2250102030405',
            user_type=User.UserType.ETUDIANT,
        )
        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_inscription=2026,
        )
        return user, etudiant

    def _create_bibliothecaire(self):
        user = User.objects.create_user(
            email='biblio@example.com',
            password='Password123!',
            first_name='Mariam',
            last_name='Kone',
            phone='+2250102030406',
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        bibliothecaire = Bibliothecaire.objects.create(
            user=user,
            badge_number='BIB-001',
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=True,
        )
        return user, bibliothecaire

    def _create_admin(self):
        return User.objects.create_superuser(
            email='admin@example.com',
            password='Password123!',
            first_name='Grace',
            last_name='Hopper',
            phone='+2250102030407',
        )

    def test_etudiant_can_consult_his_profile(self):
        user, etudiant = self._create_etudiant()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], User.UserType.ETUDIANT)
        self.assertEqual(response.data['data']['profil']['etudiant_id'], str(etudiant.id))
        self.assertEqual(response.data['data']['profil']['matricule'], etudiant.matricule)
        self.assertEqual(response.data['data']['profil']['filiere']['name'], self.filiere.name)

    def test_bibliothecaire_can_consult_his_profile(self):
        user, bibliothecaire = self._create_bibliothecaire()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], User.UserType.BIBLIOTHECAIRE)
        self.assertEqual(
            response.data['data']['profil']['bibliothecaire_id'],
            str(bibliothecaire.id),
        )
        self.assertTrue(response.data['data']['profil']['peut_gerer_utilisateurs'])

    def test_admin_can_consult_his_profile(self):
        admin = self._create_admin()
        self.client.force_authenticate(user=admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], User.UserType.ADMINISTRATEUR)
        self.assertTrue(response.data['data']['profil']['is_superuser'])

    def test_user_can_update_birth_date_and_avatar(self):
        user, _ = self._create_etudiant()
        self.client.force_authenticate(user=user)
        avatar = SimpleUploadedFile(
            'avatar.gif',
            (
                b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
                b'\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00'
                b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

        response = self.client.patch(
            self.url,
            {'date_of_birth': '2001-05-14', 'avatar': avatar},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(str(user.date_of_birth), '2001-05-14')
        self.assertTrue(user.avatar.name)
        self.assertIsNotNone(response.data['data']['avatar_url'])
