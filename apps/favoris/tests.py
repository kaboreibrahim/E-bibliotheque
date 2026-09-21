from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, TypeDocument
from apps.favoris.models import Favori
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant

User = get_user_model()


class FavoriIdorTests(APITestCase):
    """SEC-004 : un etudiant ne doit jamais pouvoir agir sur les favoris d'un autre."""

    def setUp(self):
        filiere = Filiere.objects.create(name="Droit Favoris")
        niveau = Niveau.objects.create(filiere=filiere, name=Niveau.NiveauChoices.L1)
        specialite = Specialite.objects.create(name="Generale Favoris", niveau=niveau)

        self.user_a = User.objects.create_user(
            email="etu.a@example.com", password="Password123!",
            first_name="A", last_name="Etudiant", phone="+2250700000010",
            user_type=User.UserType.ETUDIANT,
        )
        self.etudiant_a = Etudiant.objects.create(
            user=self.user_a, filiere=filiere, niveau=niveau, specialite=specialite,
        )

        self.user_b = User.objects.create_user(
            email="etu.b@example.com", password="Password123!",
            first_name="B", last_name="Etudiant", phone="+2250700000011",
            user_type=User.UserType.ETUDIANT,
        )
        self.etudiant_b = Etudiant.objects.create(
            user=self.user_b, filiere=filiere, niveau=niveau, specialite=specialite,
        )

        type_cours, _ = TypeDocument.objects.get_or_create(
            code=TypeDocument.COURS, defaults={"name": "Cours"},
        )
        self.document = Document.objects.create(
            title="Cours de favoris",
            type=type_cours,
            file_path=SimpleUploadedFile("cours.pdf", b"test", content_type="application/pdf"),
            filiere=filiere, niveau=niveau, specialite=specialite,
            annee_academique_debut=2025,
        )

        self.favori_b = Favori.objects.create(etudiant=self.etudiant_b, document=self.document)

    def test_etudiant_ne_peut_pas_lister_les_favoris_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get("/api/favoris/favoris/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data]
        self.assertNotIn(str(self.favori_b.pk), ids)

    def test_etudiant_ne_peut_pas_lire_le_favori_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(f"/api/favoris/favoris/{self.favori_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_etudiant_ne_peut_pas_supprimer_le_favori_dun_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.delete(f"/api/favoris/favoris/{self.favori_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Favori.objects.filter(pk=self.favori_b.pk).exists())

    def test_etudiant_ne_peut_pas_creer_un_favori_pour_un_autre(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/favoris/favoris/",
            {"etudiant": str(self.etudiant_b.pk), "document": str(self.document.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        favori = Favori.objects.get(pk=response.data["id"])
        # Le champ "etudiant" envoye par le client est ignore : le favori est bien le sien.
        self.assertEqual(favori.etudiant_id, self.etudiant_a.pk)

    def test_etudiant_peut_gerer_ses_propres_favoris(self):
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(f"/api/favoris/favoris/{self.favori_b.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        create_response = self.client.post(
            "/api/favoris/favoris/", {"document": str(self.document.pk)},
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        favori_id = create_response.data["id"]

        get_response = self.client.get(f"/api/favoris/favoris/{favori_id}/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(f"/api/favoris/favoris/{favori_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_etudiant_recoit_403(self):
        admin = User.objects.create_superuser(
            email="admin.favoris@example.com", password="Password123!",
            first_name="Admin", last_name="Favoris", phone="+2250700000012",
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get("/api/favoris/favoris/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
