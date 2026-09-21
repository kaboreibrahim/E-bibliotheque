from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite

User = get_user_model()


class ConsultationIdorTests(APITestCase):
    """SEC-005 : un utilisateur ne doit jamais pouvoir agir sur l'historique d'un autre."""

    def setUp(self):
        filiere = Filiere.objects.create(name="Droit Consultations")
        niveau = Niveau.objects.create(filiere=filiere, name=Niveau.NiveauChoices.L1)
        specialite = Specialite.objects.create(name="Generale Consultations", niveau=niveau)

        self.user_a = User.objects.create_user(
            email="cons.a@example.com", password="Password123!",
            first_name="A", last_name="User", phone="+2250700000020",
            user_type=User.UserType.ETUDIANT,
        )
        self.user_b = User.objects.create_user(
            email="cons.b@example.com", password="Password123!",
            first_name="B", last_name="User", phone="+2250700000021",
            user_type=User.UserType.ETUDIANT,
        )

        type_cours, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.COURS, defaults={"name": "Cours"},
        )
        self.document = Document.objects.create(
            title="Cours de consultation",
            type=type_cours,
            file_path=SimpleUploadedFile("cours.pdf", b"test", content_type="application/pdf"),
            filiere=filiere, niveau=niveau, specialite=specialite,
            annee_academique_debut=2025,
        )

        self.consultation_b = Consultation.objects.create(
            user=self.user_b,
            type_consultation=Consultation.TypeConsultation.VUE,
            document=self.document,
        )

    def test_utilisateur_ne_peut_pas_lister_lhistorique_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/consultations/consultations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data]
        self.assertNotIn(str(self.consultation_b.pk), ids)

    def test_utilisateur_ne_peut_pas_lire_une_consultation_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(f"/api/consultations/consultations/{self.consultation_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_utilisateur_ne_peut_pas_supprimer_une_consultation_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(f"/api/consultations/consultations/{self.consultation_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Consultation.objects.filter(pk=self.consultation_b.pk).exists())

    def test_utilisateur_ne_peut_pas_terminer_une_consultation_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.patch(f"/api/consultations/consultations/{self.consultation_b.pk}/terminer/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.consultation_b.refresh_from_db()
        self.assertIsNone(self.consultation_b.fin_consultation)

    def test_en_cours_ne_retourne_que_les_siennes(self):
        Consultation.objects.create(
            user=self.user_a,
            type_consultation=Consultation.TypeConsultation.VUE,
            document=self.document,
        )
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/consultations/consultations/en-cours/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data:
            self.assertEqual(item["user"], str(self.user_a.pk))

    def test_vue_est_toujours_attribuee_a_lutilisateur_connecte(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/consultations/consultations/vue/",
            {"document": str(self.document.pk), "user": str(self.user_b.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        consultation = Consultation.objects.get(pk=response.data["id"])
        # Le champ "user" envoye par le client est ignore.
        self.assertEqual(consultation.user_id, self.user_a.pk)

    def test_utilisateur_peut_gerer_ses_propres_consultations(self):
        self.client.force_authenticate(user=self.user_b)

        get_response = self.client.get(f"/api/consultations/consultations/{self.consultation_b.pk}/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        terminer_response = self.client.patch(
            f"/api/consultations/consultations/{self.consultation_b.pk}/terminer/"
        )
        self.assertEqual(terminer_response.status_code, status.HTTP_200_OK)
