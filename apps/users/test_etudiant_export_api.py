from io import BytesIO
from zipfile import ZipFile

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, PersonneExterne, User


class EtudiantExportExcelApiTests(APITestCase):
    def setUp(self):
        self.url = reverse('etudiants:etudiant-export-excel')
        self.filiere = Filiere.objects.create(name='Informatique')
        self.niveau_m1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M1,
        )
        self.niveau_m2 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M2,
        )
        self.specialite_m1 = Specialite.objects.create(
            name='Reseaux',
            niveau=self.niveau_m1,
        )
        self.specialite_m2 = Specialite.objects.create(
            name='IA',
            niveau=self.niveau_m2,
        )
        self.admin = User.objects.create_superuser(
            email='admin-export@example.com',
            password='Password123!',
            first_name='Admin',
            last_name='Export',
            phone='+2250102030490',
        )
        self.biblio = User.objects.create_user(
            email='biblio-export@example.com',
            password='Password123!',
            first_name='Biblio',
            last_name='Export',
            phone='+2250102030491',
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(
            user=self.biblio,
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=False,
        )

    def _create_student(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        phone: str,
        niveau,
        specialite,
    ):
        user = User.objects.create_user(
            email=email,
            password='Password123!',
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=User.UserType.ETUDIANT,
        )
        return Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=niveau,
            specialite=specialite,
            annee_inscription=2026,
        )

    def _read_sheet_xml(self, response) -> str:
        archive = ZipFile(BytesIO(response.content))
        return archive.read('xl/worksheets/sheet1.xml').decode('utf-8')

    def test_admin_can_export_students_to_excel(self):
        etudiant = self._create_student(
            email='awa@example.com',
            first_name='Awa',
            last_name='Traore',
            phone='+2250102030405',
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('.xlsx', response['Content-Disposition'])

        sheet_xml = self._read_sheet_xml(response)
        self.assertIn('Matricule', sheet_xml)
        self.assertIn(etudiant.matricule, sheet_xml)
        self.assertIn('awa@example.com', sheet_xml)
        self.assertIn('Reseaux', sheet_xml)
        self.assertIn('Informatique', sheet_xml)
        self.assertIn('Etudiant', sheet_xml)

    def test_export_applies_search_filters(self):
        self._create_student(
            email='awa@example.com',
            first_name='Awa',
            last_name='Traore',
            phone='+2250102030405',
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
        )
        self._create_student(
            email='binta@example.com',
            first_name='Binta',
            last_name='Diallo',
            phone='+2250102030406',
            niveau=self.niveau_m2,
            specialite=self.specialite_m2,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f'{self.url}?search=awa')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet_xml = self._read_sheet_xml(response)
        self.assertIn('awa@example.com', sheet_xml)
        self.assertNotIn('binta@example.com', sheet_xml)

    def test_export_includes_external_person_with_profile_type(self):
        user = User.objects.create_user(
            email='externe@example.com',
            password='Password123!',
            first_name='Koffi',
            last_name='Extern',
            phone='+2250102030410',
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        PersonneExterne.objects.create(
            user=user,
            numero_piece='CNI-998877',
            profession='Consultant',
            lieu_habitation='Abidjan',
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet_xml = self._read_sheet_xml(response)
        self.assertIn('Personne externe', sheet_xml)
        self.assertIn('externe@example.com', sheet_xml)
        self.assertIn('CNI-998877', sheet_xml)
        self.assertIn('Consultant', sheet_xml)
        self.assertIn('Abidjan', sheet_xml)

    def test_bibliothecaire_can_export_students_to_excel(self):
        self._create_student(
            email='awa@example.com',
            first_name='Awa',
            last_name='Traore',
            phone='+2250102030405',
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
        )
        self.client.force_authenticate(user=self.biblio)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_export_students_to_excel(self):
        student_user = User.objects.create_user(
            email='student-export@example.com',
            password='Password123!',
            first_name='Student',
            last_name='Export',
            phone='+2250102030492',
            user_type=User.UserType.ETUDIANT,
        )
        Etudiant.objects.create(
            user=student_user,
            filiere=self.filiere,
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
            annee_inscription=2026,
        )
        self.client.force_authenticate(user=student_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
