from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.consultations.models import Consultation
from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire

User = get_user_model()


class DocumentSpecialiteRulesTests(TestCase):
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.niveau_l3 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L3)
        self.specialite_l1 = Specialite.objects.create(name="Contentieux L1", niveau=self.niveau_l1)

    def _build_document(self, *, niveau, specialite, annee_academique_debut=2024):
        return Document(
            title="Cours de procedure",
            type=TypeDocument.COURS,
            file_path=SimpleUploadedFile("cours.pdf", b"test", content_type="application/pdf"),
            filiere=self.filiere,
            niveau=niveau,
            specialite=specialite,
            annee_academique_debut=annee_academique_debut,
            encadreur="Pr. Konan",
        )

    def test_requires_academic_year_on_document_creation(self):
        document = self._build_document(
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
            annee_academique_debut=None,
        )

        with self.assertRaises(ValidationError) as ctx:
            document.full_clean()

        self.assertIn("annee_academique_debut", ctx.exception.message_dict)

    def test_formats_old_academic_year(self):
        document = self._build_document(
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
            annee_academique_debut=1960,
        )

        document.full_clean()

        self.assertEqual(document.annee_academique, "1960-1961")

    def test_requires_specialite_for_l1_documents(self):
        document = self._build_document(niveau=self.niveau_l1, specialite=None)

        with self.assertRaises(ValidationError) as ctx:
            document.full_clean()

        self.assertIn("specialite", ctx.exception.message_dict)

    def test_allows_l1_document_with_matching_specialite(self):
        document = self._build_document(niveau=self.niveau_l1, specialite=self.specialite_l1)

        document.full_clean()

    def test_requires_specialite_for_l3_documents(self):
        document = self._build_document(niveau=self.niveau_l3, specialite=None)

        with self.assertRaises(ValidationError) as ctx:
            document.full_clean()

        self.assertIn("specialite", ctx.exception.message_dict)

    def test_allows_l3_document_with_matching_specialite(self):
        specialite_l3 = Specialite.objects.create(name="Contentieux L3", niveau=self.niveau_l3)
        document = self._build_document(niveau=self.niveau_l3, specialite=specialite_l3)

        document.full_clean()


class DocumentOpenApiTests(APITestCase):
    def setUp(self):
        self.log_document_patcher = patch(
            "apps.documents.services.HistoriqueActionService.log_document",
            return_value=None,
        )
        self.log_document_patcher.start()
        self.addCleanup(self.log_document_patcher.stop)

        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L1,
        )
        self.specialite_l1 = Specialite.objects.create(
            name="Contentieux L1",
            niveau=self.niveau_l1,
        )
        self.user = User.objects.create_user(
            email="reader@example.com",
            password="Password123",
            first_name="Marie",
            last_name="Curie",
            phone="+2250708091011",
            user_type=User.UserType.ETUDIANT,
        )
        self.admin = User.objects.create_superuser(
            email="admin-doc@example.com",
            password="Password123",
            first_name="Admin",
            last_name="Doc",
            phone="+2250708091012",
        )
        self.biblio = User.objects.create_user(
            email="biblio-doc@example.com",
            password="Password123",
            first_name="Biblio",
            last_name="Doc",
            phone="+2250708091013",
            user_type=User.UserType.BIBLIOTHECAIRE,
        )
        Bibliothecaire.objects.create(
            user=self.biblio,
            peut_gerer_documents=True,
            peut_gerer_utilisateurs=False,
        )
        self.document = Document.objects.create(
            title="Cours de procedure",
            type=TypeDocument.COURS,
            file_path=SimpleUploadedFile("cours.pdf", b"test", content_type="application/pdf"),
            filiere=self.filiere,
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
            annee_academique_debut=2024,
            encadreur="Pr. Konan",
        )

    def test_detail_does_not_create_consultation(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"/api/documents/{self.document.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Consultation.objects.count(), 0)

    def test_open_document_creates_consultation_automatically(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            f"/api/documents/{self.document.pk}/ouvrir/",
            HTTP_USER_AGENT="pytest-agent",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document"]["id"], str(self.document.pk))
        self.assertTrue(response.data["consultation_id"])
        self.assertTrue(response.data["document"]["file_url"].endswith(self.document.file_path.url))

        consultation = Consultation.objects.get(pk=response.data["consultation_id"])
        self.assertEqual(consultation.user, self.user)
        self.assertEqual(consultation.document, self.document)
        self.assertEqual(consultation.type_consultation, Consultation.TypeConsultation.VUE)
        self.assertEqual(consultation.ip_address, "127.0.0.1")
        self.assertEqual(consultation.user_agent, "pytest-agent")

    def test_list_documents_supports_search(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/documents/?search=procedure")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.document.pk))

    def test_admin_can_create_document(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/documents/",
            {
                "title": "Sujet d examen",
                "type": TypeDocument.EXAMEN,
                "file_path": SimpleUploadedFile(
                    "examen.pdf",
                    b"exam",
                    content_type="application/pdf",
                ),
                "description": "Examen final",
                "filiere": str(self.filiere.pk),
                "niveau": str(self.niveau_l1.pk),
                "specialite": str(self.specialite_l1.pk),
                "annee_academique_debut": 2025,
                "encadreur": "Sujet Session 1",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Sujet d examen")
        self.assertEqual(str(response.data["ajoute_par"]), str(self.admin.pk))
        self.assertEqual(Document.objects.count(), 2)

    def test_bibliothecaire_with_document_permission_can_create_document(self):
        self.client.force_authenticate(user=self.biblio)

        response = self.client.post(
            "/api/documents/",
            {
                "title": "Memoire penal",
                "type": TypeDocument.MEMOIRE,
                "file_path": SimpleUploadedFile(
                    "memoire.pdf",
                    b"memoire",
                    content_type="application/pdf",
                ),
                "description": "Memoire de master",
                "filiere": str(self.filiere.pk),
                "niveau": str(self.niveau_l1.pk),
                "specialite": str(self.specialite_l1.pk),
                "annee_academique_debut": 2025,
                "auteur": "Auteur Test",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["ajoute_par"]), str(self.biblio.pk))

    def test_student_cannot_create_document(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/documents/",
            {
                "title": "Cours interdit",
                "type": TypeDocument.COURS,
                "file_path": SimpleUploadedFile(
                    "interdit.pdf",
                    b"cours",
                    content_type="application/pdf",
                ),
                "filiere": str(self.filiere.pk),
                "niveau": str(self.niveau_l1.pk),
                "specialite": str(self.specialite_l1.pk),
                "annee_academique_debut": 2025,
                "encadreur": "Pr. Interdit",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_soft_delete_document(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f"/api/documents/{self.document.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Document.objects.count(), 0)
