"""Modification de l'email (et controle du telephone) d'un compte par l'administration."""
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Bibliothecaire, Etudiant, User


class ModificationEmailCompteTests(APITestCase):
    def setUp(self):
        patcher = patch("apps.history.models.HistoriqueActionService.log_utilisateur", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.admin = User.objects.create_superuser(
            email="admin-mail@test.ci", password="Password123!", first_name="Admin", last_name="Mail", phone="+2250102030101"
        )
        filiere = Filiere.objects.create(name="Droit")
        niveau = Niveau.objects.create(filiere=filiere, name=Niveau.NiveauChoices.L1)
        specialite = Specialite.objects.create(name="Droit prive", niveau=niveau)
        self.etu_user = User.objects.create_user(
            email="ancien@etu.ci", password="Password123!", first_name="Aya", last_name="Kouame",
            phone="+2250102030102", user_type=User.UserType.ETUDIANT,
        )
        self.etudiant = Etudiant.objects.create(user=self.etu_user, filiere=filiere, niveau=niveau, specialite=specialite)
        self.bib_user = User.objects.create_user(
            email="biblio@test.ci", password="Password123!", first_name="Awa", last_name="Coulibaly",
            phone="+2250102030103", user_type=User.UserType.BIBLIOTHECAIRE,
        )
        self.biblio = Bibliothecaire.objects.create(user=self.bib_user)
        self.client.force_authenticate(user=self.admin)

    def _patch_etudiant(self, data):
        return self.client.patch(f"/api/etudiants/{self.etudiant.pk}/", data, format="json")

    def test_admin_modifie_email_etudiant(self):
        res = self._patch_etudiant({"email": "  Nouveau@Etu.CI "})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.etu_user.refresh_from_db()
        self.assertEqual(self.etu_user.email, "nouveau@etu.ci")

    def test_admin_modifie_email_bibliothecaire(self):
        res = self.client.patch(f"/api/bibliothecaires/{self.biblio.pk}/", {"email": "awa.c@ufhb.ci"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.bib_user.refresh_from_db()
        self.assertEqual(self.bib_user.email, "awa.c@ufhb.ci")

    def test_email_deja_utilise_refuse(self):
        res = self._patch_etudiant({"email": "BIBLIO@test.ci"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data["errors"])
        self.etu_user.refresh_from_db()
        self.assertEqual(self.etu_user.email, "ancien@etu.ci")

    def test_email_d_un_compte_supprime_refuse(self):
        supprime = User.objects.create_user(
            email="parti@test.ci", password="Password123!", first_name="P", last_name="Arti",
            phone="+2250102030104", user_type=User.UserType.ETUDIANT,
        )
        supprime.delete()  # suppression logique : l'email reste pris en base
        res = self._patch_etudiant({"email": "parti@test.ci"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_garder_son_propre_email(self):
        res = self._patch_etudiant({"email": "ancien@etu.ci", "first_name": "Ayah"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_email_invalide(self):
        res = self._patch_etudiant({"email": "pas-un-email"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_telephone_deja_utilise_refuse_sans_erreur_500(self):
        res = self._patch_etudiant({"phone": "+2250102030103"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", res.data["errors"])

    def test_etudiant_ne_peut_pas_modifier(self):
        self.client.force_authenticate(user=self.etu_user)
        res = self._patch_etudiant({"email": "pirate@etu.ci"})
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
