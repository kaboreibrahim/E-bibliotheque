from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire

User = get_user_model()


class SpecialiteRulesTests(TestCase):
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.niveau_l2 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L2)
        self.niveau_l3 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L3)

    def test_allows_specialites_for_l1_and_l2(self):
        specialite_l1 = Specialite.objects.create(name="Droit des affaires L1", niveau=self.niveau_l1)
        specialite_l2 = Specialite.objects.create(name="Droit des affaires L2", niveau=self.niveau_l2)

        self.assertEqual(specialite_l1.niveau, self.niveau_l1)
        self.assertEqual(specialite_l2.niveau, self.niveau_l2)

    def test_allows_specialite_for_l3(self):
        specialite = Specialite.objects.create(name="Droit general L3", niveau=self.niveau_l3)

        self.assertEqual(specialite.niveau, self.niveau_l3)


class SpecialiteWritePermissionTests(APITestCase):
    """SEC-006 : l'ecriture doit etre reservee a Admin / Bibliothecaire autorise.

    Note : l'URL reelle est doublee (/api/specialites/specialites/, cf. TECH-006).
    """

    def setUp(self):
        self.filiere = Filiere.objects.create(name="Filiere Test Specialite")
        self.niveau = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.specialite = Specialite.objects.create(name="Specialite Test", niveau=self.niveau)

    def test_etudiant_ne_peut_pas_creer_une_specialite(self):
        etudiant = User.objects.create_user(
            email="spec.etu@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000050",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.post(
            "/api/specialites/specialites/",
            {"niveau": str(self.niveau.pk), "name": "Hack"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_etudiant_ne_peut_pas_supprimer_une_specialite(self):
        etudiant = User.objects.create_user(
            email="spec.etu2@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000051",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.delete(f"/api/specialites/specialites/{self.specialite.pk}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bibliothecaire_autorise_peut_creer(self):
        biblio = User.objects.create_user(
            email="spec.biblio@example.com", password="Password123!",
            first_name="B", last_name="Z", phone="+2250700000052",
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(user=biblio, peut_gerer_documents=True, peut_gerer_utilisateurs=False)
        self.client.force_authenticate(user=biblio)

        response = self.client.post(
            "/api/specialites/specialites/",
            {"niveau": str(self.niveau.pk), "name": "Specialite Biblio"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
