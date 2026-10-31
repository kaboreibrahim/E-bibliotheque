"""Favoris et historique vus depuis le portail lecteur."""
import shutil
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant, User

MEDIA = Path(__file__).resolve().parent / "_test_media_portail"


class PortailLecteurTests(APITestCase):
    def setUp(self):
        MEDIA.mkdir(exist_ok=True)
        media = override_settings(MEDIA_ROOT=str(MEDIA))
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(shutil.rmtree, MEDIA, ignore_errors=True)
        for cible in ("apps.documents.services.HistoriqueActionService.log_document",
                      "apps.favoris.services.HistoriqueActionService.log_favori"):
            p = patch(cible, return_value=None)
            p.start()
            self.addCleanup(p.stop)

        self.type_cours, _ = TypeDocument.objects.get_or_create(code=TypeDocument.COURS, defaults={"name": "Cours"})
        self.filiere = Filiere.objects.create(name="Droit")
        self.l1 = Niveau.objects.create(filiere=self.filiere, name="L1")
        self.l2 = Niveau.objects.create(filiere=self.filiere, name="L2")
        self.spec_l1 = Specialite.objects.create(name="Droit prive", niveau=self.l1)
        self.spec_l2 = Specialite.objects.create(name="Droit prive", niveau=self.l2)
        self.doc_l1 = self._doc("Cours L1", self.l1, self.spec_l1)
        self.doc_l2 = self._doc("Cours L2", self.l2, self.spec_l2)
        user = User.objects.create_user(email="etu-l1@test.ci", password="Password123!", first_name="E", last_name="L1",
                                        phone="+2250708000001", user_type=User.UserType.ETUDIANT)
        Etudiant.objects.create(user=user, filiere=self.filiere, niveau=self.l1, specialite=self.spec_l1)
        self.etudiant = user
        self.client.force_authenticate(user=user)

    def _doc(self, title, niveau, spec):
        name = title.lower().replace(" ", "-") + ".pdf"
        return Document.objects.create(
            title=title, type=self.type_cours, file_path=SimpleUploadedFile(name, b"%PDF-1.4", content_type="application/pdf"),
            file_name=name, file_mime_type="application/pdf", filiere=self.filiere, niveau=niveau, specialite=spec,
            annee_academique_debut=2025, auteur="Pr. Konan", file_size=2048,
        )

    def test_favori_detaille(self):
        res = self.client.post("/api/favoris/favoris/toggle/", {"document": str(self.doc_l1.pk)}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        liste = self.client.get("/api/favoris/favoris/")
        detail = liste.data["results"][0]["document_detail"]
        self.assertEqual(detail["title"], "Cours L1")
        self.assertEqual(detail["type"], TypeDocument.COURS)
        self.assertEqual(detail["auteur"], "Pr. Konan")
        self.assertEqual(detail["niveau"], "L1")
        self.doc_l1.refresh_from_db()
        self.assertEqual(detail["file_size"], self.doc_l1.file_size)

    def test_favori_refuse_au_dessus_du_niveau(self):
        res = self.client.post("/api/favoris/favoris/toggle/", {"document": str(self.doc_l2.pk)}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get("/api/favoris/favoris/").data["count"], 0)

    def test_historique_detaille(self):
        self.client.get(f"/api/documents/{self.doc_l1.pk}/ouvrir/")
        res = self.client.get("/api/consultations/consultations/", {"type": "VUE"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        detail = res.data["results"][0]["document_detail"]
        self.assertEqual(detail["title"], "Cours L1")
        self.assertEqual(detail["auteur"], "Pr. Konan")
        self.assertEqual(detail["type_name"], self.type_cours.name)
        self.assertEqual(Consultation.objects.count(), 1)
