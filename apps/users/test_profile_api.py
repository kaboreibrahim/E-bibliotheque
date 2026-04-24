import base64
import os
import shutil

from django.test import override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.documents.models import Document
from apps.documents.models.document_type_models import TypeDocument
from apps.favoris.models import Favori
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, PersonneExterne, User


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
        self.type_cours, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.COURS,
            defaults={"name": "Cours"},
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

    def _create_personne_externe(self):
        user = User.objects.create_user(
            email='externe@example.com',
            password='Password123!',
            first_name='Kouame',
            last_name='Extern',
            phone='+2250102030408',
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        personne = PersonneExterne.objects.create(
            user=user,
            numero_piece='CNI-998877',
            profession='Consultant',
            lieu_habitation='Cocody',
        )
        return user, personne

    def _build_base64_document(self, payload: bytes) -> str:
        return base64.b64encode(payload).decode('ascii')

    def _create_document(self, title: str) -> Document:
        return Document.objects.create(
            title=title,
            type=self.type_cours,
            file_base64=self._build_base64_document(title.encode('utf-8')),
            file_name=f"{title.lower().replace(' ', '-')}.pdf",
            file_mime_type='application/pdf',
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_academique_debut=2026,
            encadreur='Pr. Test',
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

    def test_etudiant_profile_returns_linked_favoris_and_consultations(self):
        user, etudiant = self._create_etudiant()
        other_user = User.objects.create_user(
            email='other-etu@example.com',
            password='Password123!',
            first_name='Other',
            last_name='Student',
            phone='+2250102030410',
            user_type=User.UserType.ETUDIANT,
        )
        other_etudiant = Etudiant.objects.create(
            user=other_user,
            filiere=self.filiere,
            niveau=self.niveau,
            specialite=self.specialite,
            annee_inscription=2026,
        )
        document_favori = self._create_document('Cours reseaux')
        document_vue = self._create_document('Memoire securite')
        other_document = self._create_document('Document autre')

        favori = Favori.objects.create(etudiant=etudiant, document=document_favori)
        Favori.objects.create(etudiant=other_etudiant, document=other_document)

        consultation_vue = Consultation.objects.create(
            user=user,
            document=document_vue,
            type_consultation=Consultation.TypeConsultation.VUE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )
        consultation_recherche = Consultation.objects.create(
            user=user,
            recherche_query='memoire droit',
            type_consultation=Consultation.TypeConsultation.RECHERCHE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )
        Consultation.objects.create(
            user=other_user,
            document=other_document,
            type_consultation=Consultation.TypeConsultation.VUE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profil = response.data['data']['profil']
        self.assertEqual(len(profil['favoris']), 1)
        self.assertEqual(profil['favoris'][0]['id'], str(favori.id))
        self.assertEqual(profil['favoris'][0]['document']['id'], str(document_favori.id))
        self.assertEqual(profil['favoris'][0]['document']['title'], document_favori.title)

        consultation_ids = {item['id'] for item in profil['consultations']}
        self.assertEqual(
            consultation_ids,
            {str(consultation_vue.id), str(consultation_recherche.id)},
        )
        vue_item = next(
            item for item in profil['consultations']
            if item['id'] == str(consultation_vue.id)
        )
        recherche_item = next(
            item for item in profil['consultations']
            if item['id'] == str(consultation_recherche.id)
        )
        self.assertEqual(vue_item['document']['id'], str(document_vue.id))
        self.assertEqual(vue_item['type_consultation'], Consultation.TypeConsultation.VUE)
        self.assertEqual(recherche_item['document'], None)
        self.assertEqual(recherche_item['recherche_query'], 'memoire droit')

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

    def test_personne_externe_profile_returns_linked_consultations(self):
        user, personne = self._create_personne_externe()
        document_vue = self._create_document('Guide bibliotheque')
        other_user, _ = self._create_etudiant()

        consultation_vue = Consultation.objects.create(
            user=user,
            document=document_vue,
            type_consultation=Consultation.TypeConsultation.VUE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
            fin_consultation=timezone.now(),
        )
        consultation_recherche = Consultation.objects.create(
            user=user,
            recherche_query='revue numerique',
            type_consultation=Consultation.TypeConsultation.RECHERCHE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )
        Consultation.objects.create(
            user=other_user,
            document=document_vue,
            type_consultation=Consultation.TypeConsultation.VUE,
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], User.UserType.PERSONNE_EXTERNE)
        profil = response.data['data']['profil']
        self.assertEqual(profil['personne_externe_id'], str(personne.id))
        self.assertEqual(profil['favoris'], [])
        consultation_ids = {item['id'] for item in profil['consultations']}
        self.assertEqual(
            consultation_ids,
            {str(consultation_vue.id), str(consultation_recherche.id)},
        )
        vue_item = next(
            item for item in profil['consultations']
            if item['id'] == str(consultation_vue.id)
        )
        self.assertEqual(vue_item['document']['title'], document_vue.title)

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
