"""
Contrôle d'accès aux documents selon le profil du lecteur.

Règle attendue :
  - un étudiant voit les documents de son niveau ET des niveaux inférieurs
    (L1 → L1 ; L2 → L1-L2 ; L3 → L1-L3 ; M1 → L1-M1 ; M2 → L1-M2 ; Doctorat → tout),
    dans sa filière uniquement ;
  - niveaux inférieurs : toutes les spécialités de la filière ;
  - son propre niveau : uniquement sa spécialité ;
  - tous les autres types de compte (administrateur, bibliothécaire,
    enseignant-chercheur, chercheur, personne externe) voient tous les documents.

Le contrôle est vérifié sur la liste, la fiche, l'ouverture (consultation) et le flux du fichier.
"""
import shutil
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, TypeDocument
from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Chercheur, EnseignantChercheur, Etudiant, PersonneExterne

User = get_user_model()
TEST_MEDIA_ROOT = Path(__file__).resolve().parent / "_test_media_acces_niveau"

NIVEAUX = ["L1", "L2", "L3", "M1", "M2", "DOCTORAT"]
SPECIALITE = "Droit prive"
PDF = b"%PDF-1.4\n%test\n"


class DocumentAccesParNiveauTests(APITestCase):
    def setUp(self):
        super().setUp()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        TEST_MEDIA_ROOT.mkdir(exist_ok=True)
        media = override_settings(MEDIA_ROOT=str(TEST_MEDIA_ROOT))
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(shutil.rmtree, TEST_MEDIA_ROOT, ignore_errors=True)
        patcher = patch("apps.documents.services.HistoriqueActionService.log_document", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.type_cours, _ = TypeDocument.objects.get_or_create(code=TypeDocument.COURS, defaults={"name": "Cours"})
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveaux = {}
        self.specialites = {}
        self.docs = {}  # un document par niveau, dans la spécialité « Droit prive »
        for code in NIVEAUX:
            niveau = Niveau.objects.create(filiere=self.filiere, name=code)
            self.niveaux[code] = niveau
            self.specialites[code] = Specialite.objects.create(name=SPECIALITE, niveau=niveau)
            self.docs[code] = self._doc(f"Cours {code}", self.filiere, niveau, self.specialites[code])

        # Un document par niveau dans une autre spécialité (« Droit public »)
        self.docs_autre_spec = {}
        for code in NIVEAUX:
            spec = Specialite.objects.create(name="Droit public", niveau=self.niveaux[code])
            self.docs_autre_spec[code] = self._doc(f"Cours {code} Droit public", self.filiere, self.niveaux[code], spec)
        # Document d'une autre filière : jamais visible par un étudiant de Droit
        eco = Filiere.objects.create(name="Economie")
        eco_l1 = Niveau.objects.create(filiere=eco, name="L1")
        self.doc_autre_filiere = self._doc("Cours L1 Economie", eco, eco_l1, Specialite.objects.create(name=SPECIALITE, niveau=eco_l1))

        self.all_ids = {str(d.pk) for d in Document.objects.all()}
        self._phone = 1000

    # ── Fabriques ────────────────────────────────────────────────────────────
    def _doc(self, title, filiere, niveau, specialite):
        name = title.lower().replace(" ", "-") + ".pdf"
        return Document.objects.create(
            title=title,
            type=self.type_cours,
            file_path=SimpleUploadedFile(name, PDF, content_type="application/pdf"),
            file_name=name,
            file_mime_type="application/pdf",
            filiere=filiere,
            niveau=niveau,
            specialite=specialite,
            annee_academique_debut=2025,
        )

    def _user(self, user_type, label):
        self._phone += 1
        return User.objects.create_user(
            email=f"{label.lower()}@test.ci",
            password="Password123",
            first_name="Test",
            last_name=label,
            phone=f"+225070800{self._phone}",
            user_type=user_type,
        )

    def _etudiant(self, code):
        user = self._user(User.UserType.ETUDIANT, f"etu-{code}")
        Etudiant.objects.create(user=user, filiere=self.filiere, niveau=self.niveaux[code], specialite=self.specialites[code])
        return user

    def _ids(self, user):
        self.client.force_authenticate(user=user)
        res = self.client.get("/api/documents/", {"page_size": 200})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return {item["id"] for item in res.data["results"]}

    def _access(self, user, doc):
        """Codes HTTP de la fiche, de l'ouverture et du flux du fichier."""
        self.client.force_authenticate(user=user)
        return [
            self.client.get(f"/api/documents/{doc.pk}/").status_code,
            self.client.get(f"/api/documents/{doc.pk}/ouvrir/").status_code,
            self.client.get(f"/api/documents/{doc.pk}/fichier/").status_code,
        ]

    # ── Étudiants : niveau courant + niveaux inférieurs ─────────────────────
    def _attendus(self, rang):
        """Sa spécialité jusqu'à son niveau + les autres spécialités des niveaux inférieurs."""
        ids = {str(self.docs[c].pk) for c in NIVEAUX[: rang + 1]}
        ids |= {str(self.docs_autre_spec[c].pk) for c in NIVEAUX[:rang]}
        return ids

    def test_etudiant_voit_son_niveau_et_les_niveaux_inferieurs(self):
        for rang, code in enumerate(NIVEAUX):
            with self.subTest(niveau=code):
                self.assertSetEqual(self._ids(self._etudiant(code)), self._attendus(rang))

    def test_etudiant_ne_peut_ouvrir_que_les_niveaux_autorises(self):
        ok, refuse = [status.HTTP_200_OK] * 3, [status.HTTP_404_NOT_FOUND] * 3
        for rang, code in enumerate(NIVEAUX):
            etudiant = self._etudiant(code)
            for rang_doc, code_doc in enumerate(NIVEAUX):
                with self.subTest(etudiant=code, document=code_doc, specialite="la sienne"):
                    self.assertEqual(self._access(etudiant, self.docs[code_doc]), ok if rang_doc <= rang else refuse)
                with self.subTest(etudiant=code, document=code_doc, specialite="autre"):
                    self.assertEqual(self._access(etudiant, self.docs_autre_spec[code_doc]), ok if rang_doc < rang else refuse)

    def test_etudiant_ne_voit_pas_autre_specialite_de_son_niveau_ni_autre_filiere(self):
        for code in NIVEAUX:
            with self.subTest(niveau=code):
                etudiant = self._etudiant(code)
                ids = self._ids(etudiant)
                self.assertNotIn(str(self.docs_autre_spec[code].pk), ids)
                self.assertNotIn(str(self.doc_autre_filiere.pk), ids)
                self.assertEqual(self._access(etudiant, self.doc_autre_filiere), [status.HTTP_404_NOT_FOUND] * 3)

    def test_niveaux_inferieurs_toutes_specialites_meme_si_nom_different(self):
        """Ex. spécialité « Tronc commun L1 » puis « Tronc commun L2 » : le L2 voit bien le L1."""
        tc_l1 = Specialite.objects.create(name="Tronc commun L1", niveau=self.niveaux["L1"])
        tc_l2 = Specialite.objects.create(name="Tronc commun L2", niveau=self.niveaux["L2"])
        doc_tc_l1 = self._doc("Cours tronc commun L1", self.filiere, self.niveaux["L1"], tc_l1)
        user = self._user(User.UserType.ETUDIANT, "etu-tc-l2")
        Etudiant.objects.create(user=user, filiere=self.filiere, niveau=self.niveaux["L2"], specialite=tc_l2)
        self.assertIn(str(doc_tc_l1.pk), self._ids(user))
        self.assertEqual(self._access(user, doc_tc_l1), [status.HTTP_200_OK] * 3)

    def test_filtre_niveau_ne_contourne_pas_la_restriction(self):
        etudiant_l1 = self._etudiant("L1")
        self.client.force_authenticate(user=etudiant_l1)
        res = self.client.get("/api/documents/", {"niveau": str(self.niveaux["M2"].pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], [])

    # ── Autres comptes : accès à tout le catalogue ──────────────────────────
    def test_autres_comptes_voient_tous_les_documents(self):
        admin = User.objects.create_superuser(email="admin@test.ci", password="Password123", first_name="A", last_name="Admin", phone="+2250708099001")
        biblio = self._user(User.UserType.BIBLIOTHECAIRE, "biblio")
        Bibliothecaire.objects.create(user=biblio, peut_gerer_documents=True, peut_gerer_utilisateurs=False)
        enseignant = self._user(User.UserType.ENSEIGNANT_CHERCHEUR, "enseignant")
        EnseignantChercheur.objects.create(user=enseignant)
        chercheur = self._user(User.UserType.CHERCHEUR, "chercheur")
        Chercheur.objects.create(user=chercheur)
        externe = self._user(User.UserType.PERSONNE_EXTERNE, "externe")
        PersonneExterne.objects.create(user=externe, numero_piece="CNI-1", profession="Avocat", lieu_habitation="Abidjan")

        for label, user in [("administrateur", admin), ("bibliothécaire", biblio), ("enseignant-chercheur", enseignant), ("chercheur", chercheur), ("personne externe", externe)]:
            with self.subTest(compte=label):
                self.assertSetEqual(self._ids(user), self.all_ids)
                self.assertEqual(self._access(user, self.docs["DOCTORAT"]), [status.HTTP_200_OK] * 3)
                self.assertEqual(self._access(user, self.doc_autre_filiere), [status.HTTP_200_OK] * 3)
