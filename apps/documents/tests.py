import base64

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.consultations.models import Consultation
from apps.documents.models import Document, TypeDocument
from apps.documents.utils import build_document_data_uri
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, PersonneExterne

User = get_user_model()


class DocumentSpecialiteRulesTests(TestCase):
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.niveau_l3 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L3)
        self.specialite_l1 = Specialite.objects.create(name="Contentieux L1", niveau=self.niveau_l1)
        self.type_cours, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.COURS,
            defaults={"name": "Cours"},
        )

    def _build_document(self, *, niveau, specialite, annee_academique_debut=2024):
        return Document(
            title="Cours de procedure",
            type=self.type_cours,
            file_base64=base64.b64encode(b"test").decode("ascii"),
            file_name="cours.pdf",
            file_mime_type="application/pdf",
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
    def _build_base64_document(self, content: bytes) -> str:
        return base64.b64encode(content).decode("ascii")

    def _create_document(
        self,
        *,
        title: str,
        niveau,
        specialite,
        encadreur: str = "Pr. Konan",
    ) -> Document:
        return Document.objects.create(
            title=title,
            type=self.type_cours,
            file_base64=self._build_base64_document(title.encode("utf-8")),
            file_name=f"{title.lower().replace(' ', '-')}.pdf",
            file_mime_type="application/pdf",
            filiere=self.filiere,
            niveau=niveau,
            specialite=specialite,
            annee_academique_debut=2024,
            encadreur=encadreur,
        )

    def _create_student(self, *, email: str, phone: str, niveau, specialite):
        user = User.objects.create_user(
            email=email,
            password="Password123",
            first_name="Student",
            last_name=niveau.name,
            phone=phone,
            user_type=User.UserType.ETUDIANT,
        )
        Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=niveau,
            specialite=specialite,
        )
        return user

    def _create_external(self, *, email: str, phone: str):
        user = User.objects.create_user(
            email=email,
            password="Password123",
            first_name="External",
            last_name="Reader",
            phone=phone,
            user_type=User.UserType.PERSONNE_EXTERNE,
        )
        PersonneExterne.objects.create(
            user=user,
            numero_piece="CNI-445566",
            profession="Consultant",
            lieu_habitation="Abidjan",
        )
        return user

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
        self.niveau_l2 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L2,
        )
        self.niveau_l3 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L3,
        )
        self.niveau_m1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M1,
        )
        self.niveau_m2 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M2,
        )
        self.specialite_l1 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l1,
        )
        self.specialite_l2 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l2,
        )
        self.specialite_l3 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l3,
        )
        self.specialite_m1 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_m1,
        )
        self.specialite_m2 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_m2,
        )
        self.specialite_alt_l1 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_l1,
        )
        self.specialite_alt_l2 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_l2,
        )
        self.specialite_alt_l3 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_l3,
        )
        self.specialite_alt_m1 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_m1,
        )
        self.other_filiere = Filiere.objects.create(name="Economie")
        self.other_niveau_l1 = Niveau.objects.create(
            filiere=self.other_filiere,
            name=Niveau.NiveauChoices.L1,
        )
        self.other_specialite_l1 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.other_niveau_l1,
        )
        self.user = User.objects.create_user(
            email="reader@example.com",
            password="Password123",
            first_name="Marie",
            last_name="Curie",
            phone="+2250708091011",
            user_type=User.UserType.ETUDIANT,
        )
        Etudiant.objects.create(
            user=self.user,
            filiere=self.filiere,
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
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
        self.type_cours, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.COURS,
            defaults={"name": "Cours"},
        )
        self.type_examen, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.EXAMEN,
            defaults={"name": "Examen"},
        )
        self.type_memoire, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.MEMOIRE,
            defaults={"name": "Memoire"},
        )
        self.type_these, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.THESE,
            defaults={"name": "These"},
        )
        self.document_base64 = self._build_base64_document(b"test")
        self.document = Document.objects.create(
            title="Cours de procedure",
            type=self.type_cours,
            file_base64=self.document_base64,
            file_name="cours.pdf",
            file_mime_type="application/pdf",
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
        self.assertEqual(response.data["file_base64"], self.document_base64)
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
        self.assertEqual(response.data["document"]["file_base64"], self.document_base64)
        self.assertEqual(
            response.data["document"]["file_data_uri"],
            build_document_data_uri(self.document_base64, "application/pdf"),
        )

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
        self.assertIsNone(response.data[0]["file_base64"])

    def test_student_list_is_limited_to_his_specialite_and_lower_levels(self):
        document_l2 = self._create_document(
            title="Cours L2",
            niveau=self.niveau_l2,
            specialite=self.specialite_l2,
        )
        self._create_document(
            title="Cours L1 autre specialite",
            niveau=self.niveau_l1,
            specialite=self.specialite_alt_l1,
        )
        self._create_document(
            title="Cours L2 autre specialite",
            niveau=self.niveau_l2,
            specialite=self.specialite_alt_l2,
        )
        self._create_document(
            title="Cours L3",
            niveau=self.niveau_l3,
            specialite=self.specialite_l3,
        )
        Document.objects.create(
            title="Cours autre filiere",
            type=self.type_cours,
            file_base64=self._build_base64_document(b"other-filiere"),
            file_name="cours-autre-filiere.pdf",
            file_mime_type="application/pdf",
            filiere=self.other_filiere,
            niveau=self.other_niveau_l1,
            specialite=self.other_specialite_l1,
            annee_academique_debut=2024,
            encadreur="Pr. Economie",
        )
        user_l2 = self._create_student(
            email="reader-l2@example.com",
            phone="+2250708091091",
            niveau=self.niveau_l2,
            specialite=self.specialite_l2,
        )
        self.client.force_authenticate(user=user_l2)

        response = self.client.get("/api/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(
            returned_ids,
            {str(self.document.pk), str(document_l2.pk)},
        )

    def test_master_student_sees_master_and_lower_levels_only(self):
        document_l2 = self._create_document(
            title="Cours Master L2",
            niveau=self.niveau_l2,
            specialite=self.specialite_l2,
        )
        document_l3 = self._create_document(
            title="Cours Master L3",
            niveau=self.niveau_l3,
            specialite=self.specialite_l3,
        )
        document_m1 = self._create_document(
            title="Cours Master M1",
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
        )
        self._create_document(
            title="Cours Master M1 autre specialite",
            niveau=self.niveau_m1,
            specialite=self.specialite_alt_m1,
        )
        self._create_document(
            title="Cours Master M2",
            niveau=self.niveau_m2,
            specialite=self.specialite_m2,
        )
        user_m1 = self._create_student(
            email="reader-m1@example.com",
            phone="+2250708091092",
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
        )
        self.client.force_authenticate(user=user_m1)

        response = self.client.get("/api/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertSetEqual(
            returned_ids,
            {
                str(self.document.pk),
                str(document_l2.pk),
                str(document_l3.pk),
                str(document_m1.pk),
            },
        )

    def test_student_cannot_access_document_above_his_level(self):
        document_l2 = self._create_document(
            title="Cours reserve L2",
            niveau=self.niveau_l2,
            specialite=self.specialite_l2,
        )
        self.client.force_authenticate(user=self.user)

        detail_response = self.client.get(f"/api/documents/{document_l2.pk}/")
        open_response = self.client.get(f"/api/documents/{document_l2.pk}/ouvrir/")

        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(open_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_access_document_from_other_specialite(self):
        document_other_specialite = self._create_document(
            title="Cours reserve autre specialite",
            niveau=self.niveau_l1,
            specialite=self.specialite_alt_l1,
        )
        self.client.force_authenticate(user=self.user)

        detail_response = self.client.get(f"/api/documents/{document_other_specialite.pk}/")
        open_response = self.client.get(f"/api/documents/{document_other_specialite.pk}/ouvrir/")

        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(open_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_external_person_can_access_all_documents(self):
        document_l2 = self._create_document(
            title="Cours externe L2",
            niveau=self.niveau_l2,
            specialite=self.specialite_l2,
        )
        document_m2 = self._create_document(
            title="Cours externe M2",
            niveau=self.niveau_m2,
            specialite=self.specialite_m2,
        )
        external_user = self._create_external(
            email="external.reader@example.com",
            phone="+2250708091093",
        )
        self.client.force_authenticate(user=external_user)

        list_response = self.client.get("/api/documents/")
        detail_response = self.client.get(f"/api/documents/{document_m2.pk}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in list_response.data}
        self.assertSetEqual(
            returned_ids,
            {str(self.document.pk), str(document_l2.pk), str(document_m2.pk)},
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(document_m2.pk))

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
        self.assertEqual(response.data["file_base64"], base64.b64encode(b"exam").decode("ascii"))
        self.assertEqual(Document.objects.count(), 2)
        created_document = Document.objects.exclude(pk=self.document.pk).get()
        self.assertEqual(created_document.file_base64, base64.b64encode(b"exam").decode("ascii"))
        self.assertEqual(created_document.file_name, "examen.pdf")

    def test_admin_can_create_document_from_base64_payload(self):
        self.client.force_authenticate(user=self.admin)

        raw_base64 = base64.b64encode(b"memoire-json").decode("ascii")
        response = self.client.post(
            "/api/documents/",
            {
                "title": "Memoire JSON",
                "type": TypeDocument.MEMOIRE,
                "file_base64": f"data:application/pdf;base64,{raw_base64}",
                "file_name": "memoire-json.pdf",
                "file_mime_type": "application/pdf",
                "description": "Memoire envoye en JSON",
                "filiere": str(self.filiere.pk),
                "niveau": str(self.niveau_l1.pk),
                "specialite": str(self.specialite_l1.pk),
                "annee_academique_debut": 2025,
                "auteur": "Auteur JSON",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["file_base64"], raw_base64)
        created_document = Document.objects.get(title="Memoire JSON")
        self.assertEqual(created_document.file_base64, raw_base64)
        self.assertEqual(created_document.file_name, "memoire-json.pdf")

    def test_list_type_documents_returns_existing_types(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/documents/types/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_codes = {item["code"] for item in response.data}
        self.assertTrue({TypeDocument.COURS, TypeDocument.EXAMEN, TypeDocument.MEMOIRE}.issubset(returned_codes))

    def test_admin_can_create_type_document(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/documents/types/",
            {"code": "rapport", "name": "Rapport"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["code"], "RAPPORT")
        self.assertTrue(TypeDocument.objects.filter(code="RAPPORT", name="Rapport").exists())

    def test_admin_can_create_document_with_existing_custom_type(self):
        self.client.force_authenticate(user=self.admin)
        custom_type = TypeDocument.objects.create(code="RAPPORT", name="Rapport")

        raw_base64 = base64.b64encode(b"rapport-stage").decode("ascii")
        response = self.client.post(
            "/api/documents/",
            {
                "title": "Rapport de stage",
                "type": "rapport",
                "file_base64": f"data:application/pdf;base64,{raw_base64}",
                "file_name": "rapport-stage.pdf",
                "file_mime_type": "application/pdf",
                "description": "Rapport libre",
                "filiere": str(self.filiere.pk),
                "niveau": str(self.niveau_l1.pk),
                "specialite": str(self.specialite_l1.pk),
                "annee_academique_debut": 2025,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["type"], "RAPPORT")
        self.assertEqual(response.data["type_display"], "Rapport")
        created_document = Document.objects.get(title="Rapport de stage")
        self.assertEqual(created_document.type, custom_type)

    def test_list_documents_accepts_custom_type_filter(self):
        custom_type = TypeDocument.objects.create(code="RAPPORT", name="Rapport")
        custom_document = Document.objects.create(
            title="Rapport L1",
            type=custom_type,
            file_base64=self._build_base64_document(b"rapport-l1"),
            file_name="rapport-l1.pdf",
            file_mime_type="application/pdf",
            filiere=self.filiere,
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
            annee_academique_debut=2024,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/documents/?type=rapport")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [str(custom_document.pk)])

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
