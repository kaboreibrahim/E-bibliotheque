from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.users.models import Bibliothecaire

User = get_user_model()


class FiliereWritePermissionTests(APITestCase):
    """SEC-006 : l'ecriture doit etre reservee a Admin / Bibliothecaire autorise.

    Note : l'URL reelle est doublee (/api/filieres/filieres/, cf. TECH-006) tant
    que ce bug de routage n'est pas corrige.
    """

    def setUp(self):
        self.filiere = Filiere.objects.create(name="Filiere Test SEC006")

    def test_etudiant_ne_peut_pas_creer_une_filiere(self):
        etudiant = User.objects.create_user(
            email="sec006.etu@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000030",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.post("/api/filieres/filieres/", {"name": "Hack"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_etudiant_ne_peut_pas_supprimer_une_filiere(self):
        etudiant = User.objects.create_user(
            email="sec006.etu2@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000031",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.delete(f"/api/filieres/filieres/{self.filiere.pk}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Filiere.objects.filter(pk=self.filiere.pk).exists())

    def test_etudiant_peut_toujours_lister(self):
        etudiant = User.objects.create_user(
            email="sec006.etu3@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000032",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.get("/api/filieres/filieres/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bibliothecaire_autorise_peut_creer(self):
        biblio = User.objects.create_user(
            email="sec006.biblio@example.com", password="Password123!",
            first_name="B", last_name="Z", phone="+2250700000033",
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(user=biblio, peut_gerer_documents=True, peut_gerer_utilisateurs=False)
        self.client.force_authenticate(user=biblio)

        response = self.client.post("/api/filieres/filieres/", {"name": "Filiere Biblio"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_peut_supprimer(self):
        admin = User.objects.create_superuser(
            email="sec006.admin@example.com", password="Password123!",
            first_name="A", last_name="Z", phone="+2250700000034",
        )
        self.client.force_authenticate(user=admin)

        response = self.client.delete(f"/api/filieres/filieres/{self.filiere.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
