"""Recherche globale de l'administration : GET /api/recherche/."""
import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.models import ECUE, UE
from apps.users.models import Etudiant, User

URL = "/api/recherche/"
MEDIA = Path(__file__).resolve().parent / "_test_media_recherche"


class RechercheGlobaleTests(APITestCase):
    def setUp(self):
        MEDIA.mkdir(exist_ok=True)
        media = override_settings(MEDIA_ROOT=str(MEDIA))
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(shutil.rmtree, MEDIA, ignore_errors=True)

        self.admin = User.objects.create_user(email="admin@test.ci", password="Password123!", first_name="Ibrahim", last_name="Admin",
                                              phone="+2250708000201", user_type=User.UserType.ADMINISTRATEUR)
        filiere = Filiere.objects.create(name="Droit")
        l2 = Niveau.objects.create(filiere=filiere, name="L2")
        self.spec = Specialite.objects.create(name="Droit des obligations", niveau=l2)
        ue = UE.objects.create(code="DPV2101", name="Obligations civiles")
        ECUE.objects.create(ue=ue, code="DPV2101-1", name="Regime general des obligations")
        cours, _ = TypeDocument.objects.get_or_create(code=TypeDocument.COURS, defaults={"name": "Cours"})
        Document.objects.create(
            title="Cours sur les obligations", type=cours,
            file_path=SimpleUploadedFile("o.pdf", b"%PDF-1.4", content_type="application/pdf"),
            file_name="o.pdf", file_mime_type="application/pdf", filiere=filiere, niveau=l2, specialite=self.spec,
            annee_academique_debut=2025, auteur="Pr. Kouassi",
        )
        etu = User.objects.create_user(email="aya@etu.ci", password="Password123!", first_name="Aya", last_name="Kouassi",
                                       phone="+2250708000202", user_type=User.UserType.ETUDIANT)
        Etudiant.objects.create(user=etu, filiere=filiere, niveau=l2, specialite=self.spec)
        self.biblio = User.objects.create_user(email="awa@ufhb.ci", password="Password123!", first_name="Awa", last_name="Kouassi",
                                               phone="+2250708000203", user_type=User.UserType.BIBLIOTHECAIRE)
        self.etu = etu

    def _get(self, q, user=None, **extra):
        self.client.force_authenticate(user=user or self.admin)
        return self.client.get(URL, {"q": q, **extra})

    def test_groupes_et_totaux(self):
        res = self._get("oblig")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        groupes = {g["type"]: g for g in res.data["groupes"]}
        self.assertEqual(set(groupes), {"documents", "ues", "ecues", "specialites"})
        self.assertEqual(groupes["documents"]["resultats"][0]["titre"], "Cours sur les obligations")
        self.assertEqual(res.data["total"], sum(g["total"] for g in res.data["groupes"]))

    def test_comptes_par_nom(self):
        res = self._get("kouassi")
        groupes = {g["type"]: g for g in res.data["groupes"]}
        self.assertEqual(groupes["etudiants"]["resultats"][0]["email"], "aya@etu.ci")
        self.assertEqual(groupes["personnel"]["resultats"][0]["user_type"], "BIBLIOTHECAIRE")
        self.assertIn("documents", groupes)  # l'auteur « Pr. Kouassi »

    def test_matricule(self):
        matricule = Etudiant.objects.get(user=self.etu).matricule
        res = self._get(matricule)
        groupes = {g["type"]: g for g in res.data["groupes"]}
        self.assertEqual(groupes["etudiants"]["total"], 1)

    def test_limite_par_groupe(self):
        for i in range(4):
            Specialite.objects.create(name=f"Obligations speciales {i}", niveau=self.spec.niveau)
        res = self._get("oblig", limite=2)
        groupe = next(g for g in res.data["groupes"] if g["type"] == "specialites")
        self.assertEqual(groupe["total"], 5)
        self.assertEqual(len(groupe["resultats"]), 2)

    def test_texte_trop_court(self):
        self.assertEqual(self._get("o").data, {"query": "o", "total": 0, "groupes": []})

    def test_reserve_admin_et_bibliothecaire(self):
        self.assertEqual(self._get("oblig", user=self.etu).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._get("oblig", user=self.biblio).status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(URL, {"q": "oblig"}).status_code, status.HTTP_401_UNAUTHORIZED)
