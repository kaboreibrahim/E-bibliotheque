from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.users.models import Bibliothecaire

User = get_user_model()


class NiveauWritePermissionTests(APITestCase):
    """SEC-006 : l'ecriture doit etre reservee a Admin / Bibliothecaire autorise.

    Note : l'URL reelle est doublee (/api/niveaux/niveaux/, cf. TECH-006).
    """

    def setUp(self):
        self.filiere = Filiere.objects.create(name="Filiere Test Niveau")
        self.niveau = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)

    def test_etudiant_ne_peut_pas_creer_un_niveau(self):
        etudiant = User.objects.create_user(
            email="niv.etu@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000040",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.post(
            "/api/niveaux/niveaux/", {"filiere": str(self.filiere.pk), "name": "L2"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_etudiant_ne_peut_pas_supprimer_un_niveau(self):
        etudiant = User.objects.create_user(
            email="niv.etu2@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000041",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.delete(f"/api/niveaux/niveaux/{self.niveau.pk}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bibliothecaire_autorise_peut_creer(self):
        biblio = User.objects.create_user(
            email="niv.biblio@example.com", password="Password123!",
            first_name="B", last_name="Z", phone="+2250700000042",
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(user=biblio, peut_gerer_documents=True, peut_gerer_utilisateurs=False)
        self.client.force_authenticate(user=biblio)

        response = self.client.post(
            "/api/niveaux/niveaux/", {"filiere": str(self.filiere.pk), "name": "L3"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
