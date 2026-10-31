"""
Validité des comptes étudiants et année académique courante.

Règles attendues :
  - le compte est activé dès sa création ;
  - sa validité court de la date d'inscription (jour de création) jusqu'à la
    date de fin de l'année académique courante ;
  - le nombre de jours restants est calculé jusqu'à cette date de fin ;
  - une nouvelle année définie comme courante s'applique aux comptes créés
    ensuite, sans modifier les comptes existants.
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant, User


class ValiditeCompteParAnneeAcademiqueTests(APITestCase):
    def setUp(self):
        patcher = patch("apps.users.services.creation_service.HAS.log_utilisateur", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.today = timezone.localdate()
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.specialite = Specialite.objects.create(name="Droit prive", niveau=self.niveau)
        self.admin = User.objects.create_superuser(
            email="admin-annee@test.ci", password="Password123!", first_name="Admin", last_name="Annee", phone="+2250102039900"
        )
        self.client.force_authenticate(user=self.admin)
        self._n = 0

    # ── Aides ────────────────────────────────────────────────────────────────
    def _jour(self, decalage: int):
        return self.today + timedelta(days=decalage)

    def _creer_annee(self, debut, fin, courante: bool = True):
        res = self.client.post(
            "/api/annees-academiques/",
            {"date_debut": debut.isoformat(), "date_fin": fin.isoformat(), "est_courante": courante},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return res.data

    def _creer_etudiant(self, **extra):
        self._n += 1
        res = self.client.post(
            "/api/etudiants/",
            {
                "first_name": "Etudiant",
                "last_name": f"Test{self._n}",
                "email": f"etudiant{self._n}@test.ci",
                "phone": f"+22507000000{self._n:02d}",
                "password": "Motdepasse!2026",
                "confirm_password": "Motdepasse!2026",
                "filiere_id": str(self.filiere.pk),
                "niveau_id": str(self.niveau.pk),
                "specialite_id": str(self.specialite.pk),
                **extra,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        etudiant = Etudiant.objects.select_related("user").get(pk=res.data["data"]["etudiant_id"])
        return etudiant, res.data["data"]

    # ── Tests ────────────────────────────────────────────────────────────────
    def test_compte_active_des_la_creation(self):
        self._creer_annee(self._jour(-30), self._jour(200))
        etudiant, _ = self._creer_etudiant()  # sans préciser activer_immediatement

        self.assertTrue(etudiant.user.is_active)
        self.assertIsNotNone(etudiant.compte_active_le)

    def test_validite_de_l_inscription_a_la_fin_de_l_annee(self):
        self._creer_annee(self._jour(-30), self._jour(200))
        etudiant, data = self._creer_etudiant()

        self.assertEqual(etudiant.date_debut_validite, self.today)  # date d'inscription
        self.assertEqual(etudiant.date_fin_validite, self._jour(200))  # fin de l'année
        self.assertEqual(etudiant.compte_expire_le.date(), self._jour(200))
        self.assertEqual(etudiant.jours_restants, 200)
        self.assertEqual(data["jours_restants"], 200)

    def test_jours_restants_visibles_dans_la_liste(self):
        self._creer_annee(self._jour(-30), self._jour(120))
        etudiant, _ = self._creer_etudiant()

        res = self.client.get("/api/etudiants/")
        ligne = next(item for item in res.data["results"] if item["id"] == str(etudiant.pk))
        self.assertEqual(ligne["jours_restants"], 120)
        self.assertTrue(ligne["is_active"])

    def test_inscription_avant_le_debut_de_l_annee(self):
        self._creer_annee(self._jour(10), self._jour(300))
        etudiant, _ = self._creer_etudiant()

        self.assertEqual(etudiant.date_debut_validite, self._jour(10))
        self.assertEqual(etudiant.date_fin_validite, self._jour(300))

    def test_nouvelle_annee_courante_s_applique_aux_comptes_crees_ensuite(self):
        self._creer_annee(self._jour(-300), self._jour(30))
        ancien, _ = self._creer_etudiant()

        self._creer_annee(self._jour(-5), self._jour(360))  # devient l'année courante
        nouveau, _ = self._creer_etudiant()

        self.assertEqual((nouveau.date_debut_validite, nouveau.date_fin_validite), (self.today, self._jour(360)))
        ancien.refresh_from_db()
        self.assertEqual(ancien.date_fin_validite, self._jour(30))

    def test_une_annee_non_courante_n_est_pas_appliquee(self):
        self._creer_annee(self._jour(-30), self._jour(200), courante=True)
        self._creer_annee(self._jour(230), self._jour(500), courante=False)
        etudiant, _ = self._creer_etudiant()

        self.assertEqual(etudiant.date_fin_validite, self._jour(200))

    def test_creation_inactive_reste_possible_via_l_api(self):
        self._creer_annee(self._jour(-30), self._jour(200))
        etudiant, _ = self._creer_etudiant(activer_immediatement=False)

        self.assertFalse(etudiant.user.is_active)
        self.assertEqual((etudiant.date_debut_validite, etudiant.date_fin_validite), (self.today, self._jour(200)))
