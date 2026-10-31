"""Agregats du tableau de bord d'administration : /consultations/consultations/stats/overview/."""
import shutil
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import User

URL = "/api/consultations/consultations/stats/overview/"
MEDIA = Path(__file__).resolve().parent / "_test_media_overview"


class StatsOverviewTests(APITestCase):
    def setUp(self):
        MEDIA.mkdir(exist_ok=True)
        media = override_settings(MEDIA_ROOT=str(MEDIA))
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(shutil.rmtree, MEDIA, ignore_errors=True)

        self.admin = User.objects.create_user(email="admin@test.ci", password="Password123!", first_name="A", last_name="D",
                                              phone="+2250708000101", user_type=User.UserType.ADMINISTRATEUR)
        self.biblio = User.objects.create_user(email="bib@test.ci", password="Password123!", first_name="B", last_name="I",
                                               phone="+2250708000102", user_type=User.UserType.BIBLIOTHECAIRE)
        self.etu = User.objects.create_user(email="etu@test.ci", password="Password123!", first_name="E", last_name="T",
                                            phone="+2250708000103", user_type=User.UserType.ETUDIANT)
        cours, _ = TypeDocument.objects.get_or_create(code=TypeDocument.COURS, defaults={"name": "Cours"})
        filiere = Filiere.objects.create(name="Droit")
        l1 = Niveau.objects.create(filiere=filiere, name="L1")
        spec = Specialite.objects.create(name="Droit prive", niveau=l1)
        self.doc = Document.objects.create(
            title="Cours L1", type=cours, file_path=SimpleUploadedFile("c.pdf", b"%PDF-1.4", content_type="application/pdf"),
            file_name="c.pdf", file_mime_type="application/pdf", filiere=filiere, niveau=l1, specialite=spec,
            annee_academique_debut=2025, auteur="Pr. Konan",
        )
        now = timezone.now()
        # periode courante (7 jours) : 3 lectures, 1 recherche ; periode precedente : 1 lecture
        for delta in (0, 1, 1):
            Consultation.objects.create(user=self.etu, type_consultation="VUE", document=self.doc,
                                        debut_consultation=now - timedelta(days=delta), duree_secondes=600)
        Consultation.objects.create(user=self.etu, type_consultation="RECHERCHE", recherche_query="contrat",
                                    debut_consultation=now)
        Consultation.objects.create(user=self.etu, type_consultation="VUE", document=self.doc,
                                    debut_consultation=now - timedelta(days=10), duree_secondes=300)
        # une lecture effacee de l'historique par le lecteur reste comptee
        effacee = Consultation.objects.create(user=self.etu, type_consultation="VUE", document=self.doc,
                                              debut_consultation=now, duree_secondes=600)
        effacee.delete()

    def test_reserve_admin_et_bibliothecaire(self):
        self.client.force_authenticate(user=self.etu)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.biblio)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)

    def test_indicateurs_et_series(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(URL, {"jours": 7})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data
        self.assertEqual(data["periode"]["jours"], 7)
        self.assertEqual(data["kpis"]["lectures"], 4)
        self.assertEqual(data["kpis"]["recherches"], 1)
        self.assertEqual(data["kpis"]["lecteurs_actifs"], 1)
        self.assertEqual(data["kpis"]["lectures_variation"], 300.0)
        self.assertEqual(data["kpis"]["duree_moyenne_secondes"], 600)
        self.assertEqual(len(data["activite_quotidienne"]), 7)
        self.assertEqual(sum(j["lectures"] for j in data["activite_quotidienne"]), 4)
        self.assertEqual(len(data["activite_horaire"]), 24)
        self.assertEqual(len(data["documents_par_mois"]), 12)
        self.assertEqual(data["documents_par_mois"][-1]["total"], 1)
        self.assertEqual(data["documents_par_type"][0]["nb"], 1)
        self.assertEqual(data["documents_par_niveau"], [{"libelle": "L1", "nb": 1}])
        types = {u["type"]: u["total"] for u in data["utilisateurs_par_type"]}
        self.assertEqual(types["ETUDIANT"], 1)

    def test_periode_invalide(self):
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.get(URL, {"jours": "abc"}).data["periode"]["jours"], 30)
        self.assertEqual(self.client.get(URL, {"jours": 12}).data["periode"]["jours"], 30)
