from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.models import UE
from apps.ue.services import UEService
from apps.users.models import Bibliothecaire

User = get_user_model()


class UEServiceTests(TestCase):
    def setUp(self):
        self.service = UEService()
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L1,
        )
        self.niveau_l2 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L2,
        )
        self.specialite_l1 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l1,
        )
        self.specialite_l2 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l2,
        )
        self.specialite_alt_l2 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_l2,
        )

    def test_create_ue_links_specialites(self):
        ue = self.service.create_ue(
            code="ue-dr-civ-01",
            name="Droit civil",
            specialite_ids=[str(self.specialite_l1.pk), str(self.specialite_l2.pk)],
        )

        self.assertSetEqual(
            set(ue.specialites.values_list("id", flat=True)),
            {self.specialite_l1.pk, self.specialite_l2.pk},
        )

    def test_list_ues_can_filter_by_specialite(self):
        ue_prive = self.service.create_ue(
            code="UE-DR-001",
            name="UE privee",
            specialite_ids=[str(self.specialite_l2.pk)],
        )
        self.service.create_ue(
            code="UE-DR-002",
            name="UE publique",
            specialite_ids=[str(self.specialite_alt_l2.pk)],
        )

        returned_ids = set(
            self.service.list_ues(specialite_id=str(self.specialite_l2.pk)).values_list("id", flat=True)
        )

        self.assertSetEqual(returned_ids, {ue_prive.pk})


class UEWritePermissionTests(APITestCase):
    """SEC-006 : l'ecriture doit etre reservee a Admin / Bibliothecaire autorise.

    Note : l'URL reelle est doublee (/api/ues/ues/, cf. TECH-006).
    """

    def setUp(self):
        self.ue = UE.objects.create(code="UE-PERM-001", name="UE Permission Test")

    def test_etudiant_ne_peut_pas_creer_une_ue(self):
        etudiant = User.objects.create_user(
            email="ue.etu@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000060",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.post(
            "/api/ues/ues/", {"code": "UE-HACK", "name": "Hack"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_etudiant_ne_peut_pas_supprimer_une_ue(self):
        etudiant = User.objects.create_user(
            email="ue.etu2@example.com", password="Password123!",
            first_name="E", last_name="Z", phone="+2250700000061",
            user_type=User.UserType.ETUDIANT,
        )
        self.client.force_authenticate(user=etudiant)

        response = self.client.delete(f"/api/ues/ues/{self.ue.pk}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bibliothecaire_autorise_peut_creer(self):
        biblio = User.objects.create_user(
            email="ue.biblio@example.com", password="Password123!",
            first_name="B", last_name="Z", phone="+2250700000062",
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(user=biblio, peut_gerer_documents=True, peut_gerer_utilisateurs=False)
        self.client.force_authenticate(user=biblio)

        response = self.client.post(
            "/api/ues/ues/", {"code": "UE-BIBLIO-001", "name": "UE Biblio"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
