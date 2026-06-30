from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, PersonneExterne, User


class UserUpdateDetailDateOfBirthApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin-update@example.com',
            password='Password123!',
            first_name='Admin',
            last_name='Update',
            phone='+2250102030600',
        )
        self.client.force_authenticate(user=self.admin)

    def test_etudiant_patch_returns_date_of_birth(self):
        filiere = Filiere.objects.create(name='Informatique')
        niveau = Niveau.objects.create(
            filiere=filiere,
            name=Niveau.NiveauChoices.L1,
        )
        specialite = Specialite.objects.create(
            name='Genie logiciel',
            niveau=niveau,
        )
        user = User.objects.create_user(
            email='etudiant-update@example.com',
            password='Password123!',
            first_name='Awa',
            last_name='Etudiant',
            phone='+2250102030601',
            user_type=User.UserType.ETUDIANT,
        )
        etudiant = Etudiant.objects.create(
            user=user,
            filiere=filiere,
            niveau=niveau,
            specialite=specialite,
            annee_inscription=2026,
        )

        response = self.client.patch(
            reverse('etudiants:etudiant-detail', args=[etudiant.id]),
            {'date_of_birth': '2001-05-14'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(str(user.date_of_birth), '2001-05-14')
        self.assertEqual(response.data['data']['date_of_birth'], '2001-05-14')

    def test_personne_externe_patch_returns_date_of_birth(self):
        user = User.objects.create_user(
            email='externe-update@example.com',
            password='Password123!',
            first_name='Awa',
            last_name='Externe',
            phone='+2250102030602',
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        personne = PersonneExterne.objects.create(
            user=user,
            numero_piece='CNI-123456',
            profession='Consultante',
            lieu_habitation='Abidjan',
        )

        response = self.client.patch(
            reverse('personnes-externes:personne-externe-detail', args=[personne.id]),
            {'date_of_birth': '1998-08-20'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(str(user.date_of_birth), '1998-08-20')
        self.assertEqual(response.data['data']['date_of_birth'], '1998-08-20')

    def test_bibliothecaire_patch_returns_date_of_birth(self):
        user = User.objects.create_user(
            email='biblio-update@example.com',
            password='Password123!',
            first_name='Awa',
            last_name='Biblio',
            phone='+2250102030603',
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        bibliothecaire = Bibliothecaire.objects.create(
            user=user,
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=False,
        )

        response = self.client.patch(
            reverse('bibliothecaires:bibliothecaire-detail', args=[bibliothecaire.id]),
            {'date_of_birth': '1990-01-02'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(str(user.date_of_birth), '1990-01-02')
        self.assertEqual(response.data['data']['date_of_birth'], '1990-01-02')
