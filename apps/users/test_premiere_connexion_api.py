"""
Identifiants envoyés à la création d'un compte et première connexion.

Règles attendues :
  - le titulaire reçoit par email son identifiant (matricule pour un étudiant,
    email sinon) et le mot de passe temporaire ;
  - un email qui ne part pas n'empêche pas la création, mais la réponse le signale ;
  - à la première connexion, le mot de passe temporaire doit être remplacé
    (jeton à usage unique) avant la configuration de Google Authenticator.
"""
from pathlib import Path
from unittest.mock import patch

import pyotp
from django.conf import settings
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import User

URL_CHANGEMENT = "/api/auth/password/first-change/"
TEMPORAIRE = "Tempo&<raire>!26"
NOUVEAU = "Nouveau@Secret2026"


class ComptesCreesMixin:
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.specialite = Specialite.objects.create(name="Tronc commun L1", niveau=self.niveau)
        self.admin = User.objects.create_superuser(
            email="admin@test.ci", password="Password123!", first_name="Admin", last_name="Test", phone="+2250102039911"
        )

    def _creer(self, url, **extra):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            url,
            {
                "first_name": "Koffi", "last_name": "YAO", "email": "koffi.yao@test.ci", "phone": "+2250708091011",
                "password": TEMPORAIRE, "confirm_password": TEMPORAIRE, **extra,
            },
            format="json",
        )
        self.client.force_authenticate(user=None)
        return res

    def _creer_etudiant(self, **extra):
        return self._creer(
            "/api/etudiants/",
            filiere_id=str(self.filiere.pk), niveau_id=str(self.niveau.pk), specialite_id=str(self.specialite.pk), **extra,
        )


class EmailDesIdentifiantsTests(ComptesCreesMixin, APITestCase):
    def _verifier_email(self, res, identifiant):
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertTrue(res.data["data"]["email_envoye"])
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        html = msg.alternatives[0][0]
        self.assertEqual(msg.to, ["koffi.yao@test.ci"])
        self.assertEqual(msg.from_email, settings.DEFAULT_FROM_EMAIL)
        for contenu in (msg.body, html):
            self.assertIn(identifiant, contenu)
            self.assertIn("Nouveau mot de passe", contenu)
            self.assertIn("Google Authenticator", contenu)
            self.assertIn(f"{settings.FRONTEND_URL}/auth/login/", contenu)
        self.assertIn(TEMPORAIRE, msg.body)
        self.assertIn("Tempo&amp;&lt;raire&gt;!26", html)
        self.assertTrue(User.objects.get(email="koffi.yao@test.ci").must_change_password)
        return msg

    def test_etudiant_recoit_son_matricule(self):
        res = self._creer_etudiant()
        msg = self._verifier_email(res, res.data["data"]["matricule"])
        self.assertIn("Matricule : " + res.data["data"]["matricule"], msg.body)

    def test_personne_externe_recoit_son_email(self):
        res = self._creer("/api/personnes-externes/", date_debut_validite="2026-01-01", date_fin_validite="2099-12-31")
        msg = self._verifier_email(res, "koffi.yao@test.ci")
        self.assertIn("31/12/2099", msg.body)

    def test_bibliothecaire_recoit_son_email(self):
        self._verifier_email(self._creer("/api/bibliothecaires/"), "Adresse email")

    def test_enseignant_chercheur_recoit_son_email(self):
        self._verifier_email(self._creer("/api/enseignants-chercheurs/"), "Adresse email")

    def test_chercheur_recoit_son_email(self):
        self._verifier_email(self._creer("/api/chercheurs/"), "Adresse email")

    def test_logo_joint_au_message(self):
        msg = self._verifier_email(self._creer_etudiant(), "Matricule")
        self.assertIn('src="cid:logo-ufr-sjap"', msg.alternatives[0][0])
        images = [p for p in msg.message().walk() if p.get_content_maintype() == "image"]
        self.assertEqual([p["Content-ID"] for p in images], ["<logo-ufr-sjap>"])

    def test_logo_absent_n_empeche_pas_l_envoi(self):
        with patch("apps.users.services.notification_service.LOGO_PATH", Path("inexistant.jpg")):
            msg = self._verifier_email(self._creer_etudiant(), "Matricule")
        self.assertNotIn("cid:", msg.alternatives[0][0])
        self.assertEqual(msg.attachments, [])

    def test_compte_etudiant_non_active_le_precise(self):
        msg = self._verifier_email(self._creer_etudiant(activer_immediatement=False), "Matricule")
        self.assertIn("après son activation", msg.body)

    def test_echec_envoi_ne_bloque_pas_la_creation(self):
        with patch("apps.users.services.notification_service.EmailMultiAlternatives.send", side_effect=OSError("SMTP injoignable")):
            with self.assertLogs("apps.users.services.notification_service", level="ERROR") as logs:
                res = self._creer_etudiant()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertFalse(res.data["data"]["email_envoye"])
        self.assertIn("transmettez-lui vous-même", res.data["message"])
        self.assertTrue(User.objects.filter(email="koffi.yao@test.ci").exists())
        self.assertNotIn(TEMPORAIRE, "".join(logs.output))

    def test_google_authenticator_affiche_pered(self):
        for i, (url, extra) in enumerate((
            ("/api/etudiants/", {
                "filiere_id": str(self.filiere.pk), "niveau_id": str(self.niveau.pk), "specialite_id": str(self.specialite.pk),
            }),
            ("/api/bibliothecaires/", {}),
            ("/api/enseignants-chercheurs/", {}),
            ("/api/chercheurs/", {}),
        )):
            email = f"titulaire{i}@test.ci"
            res = self._creer(url, email=email, phone=f"+22507080910{i:02d}", **extra)
            self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
            totp = pyotp.parse_uri(res.data["data"]["totp_setup"]["qr_uri"])
            self.assertEqual((totp.issuer, totp.name), ("PERED", email))

    def test_creation_refusee_n_envoie_rien(self):
        self._creer_etudiant()
        mail.outbox.clear()
        res = self._creer_etudiant()  # même email
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mail.outbox, [])


class PremiereConnexionTests(ComptesCreesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.matricule = self._creer_etudiant().data["data"]["matricule"]
        self.user = User.objects.get(email="koffi.yao@test.ci")

    def _login(self, password=TEMPORAIRE):
        return self.client.post("/api/auth/etudiant/login/", {"matricule": self.matricule, "password": password}, format="json")

    def _changer(self, token, nouveau=NOUVEAU, confirmation=None):
        return self.client.post(
            URL_CHANGEMENT,
            {"change_token": token, "new_password": nouveau, "confirm_password": confirmation or nouveau},
            format="json",
        )

    def _activer_2fa(self):
        User.objects.filter(pk=self.user.pk).update(is_2fa_enabled=True)
        self.user.refresh_from_db()

    def test_parcours_complet(self):
        etape1 = self._login().data["data"]
        self.assertTrue(etape1["requires_password_change"])

        res = self._changer(etape1["password_change_token"])
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        suite = res.data["data"]
        self.assertTrue(suite["requires_totp_setup"])
        self.assertEqual(pyotp.parse_uri(suite["totp_setup"]["qr_uri"]).issuer, "PERED")
        self.assertNotIn("requires_password_change", suite)

        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertEqual(self._login().status_code, status.HTTP_401_UNAUTHORIZED)  # le temporaire ne marche plus

        code = pyotp.TOTP(suite["totp_setup"]["totp_secret"]).now()
        session = self.client.post("/api/auth/totp/confirm/", {"setup_token": suite["setup_token"], "totp_code": code}, format="json")
        self.assertEqual(session.status_code, status.HTTP_200_OK, session.data)
        self.assertIn("access", session.data["data"])
        self.assertNotIn("requires_password_change", session.data["data"])

        etape1 = self._login(NOUVEAU).data["data"]
        self.assertTrue(etape1["requires_totp"])
        self.assertNotIn("requires_password_change", etape1)

    def test_les_clients_existants_peuvent_toujours_configurer_la_2fa(self):
        """L'application mobile ne connaît pas cette étape : le QR code reste fourni à la connexion."""
        etape1 = self._login().data["data"]
        self.assertTrue(etape1["requires_totp_setup"])
        self.assertIn("totp_secret", etape1["totp_setup"])

    def test_jeton_a_usage_unique(self):
        token = self._login().data["data"]["password_change_token"]
        self.assertEqual(self._changer(token).status_code, status.HTTP_200_OK)
        res = self._changer(token, "Encore@Autre2026")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("change_token", res.data["errors"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NOUVEAU))

    def test_jeton_falsifie_ou_d_un_autre_usage(self):
        etape1 = self._login().data["data"]
        for token in ("n'importe quoi", etape1["password_change_token"] + "x", etape1["setup_token"]):
            self.assertEqual(self._changer(token).status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEMPORAIRE))

    def test_jeton_expire(self):
        token = self._login().data["data"]["password_change_token"]
        with patch("apps.users.services.auth_service.FIRST_PASSWORD_TOKEN_MAX_AGE_SECONDS", -1):
            self.assertEqual(self._changer(token).status_code, status.HTTP_400_BAD_REQUEST)

    def test_compte_desactive_entre_temps(self):
        token = self._login().data["data"]["password_change_token"]
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self._changer(token).status_code, status.HTTP_400_BAD_REQUEST)

    def test_mots_de_passe_refuses(self):
        token = self._login().data["data"]["password_change_token"]
        for nouveau, confirmation, champ in (
            (TEMPORAIRE, None, "new_password"),          # identique au temporaire
            ("12345678", None, "new_password"),          # trop courant
            ("Court1!", None, "new_password"),           # moins de 8 caractères
            ("koffi.yao@test.ci", None, "new_password"),  # trop proche de l'email
            (NOUVEAU, "Different@2026", "confirm_password"),
        ):
            res = self._changer(token, nouveau, confirmation)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, nouveau)
            self.assertIn(champ, res.data["errors"])
        self.assertEqual(self._changer(token).status_code, status.HTTP_200_OK)  # le jeton reste utilisable

    def test_jeton_obtenu_sans_totp_refuse_une_fois_la_2fa_active(self):
        token = self._login().data["data"]["password_change_token"]
        self._activer_2fa()
        self.assertEqual(self._changer(token).status_code, status.HTTP_400_BAD_REQUEST)

    def test_2fa_deja_active_le_changement_est_demande_apres_le_code(self):
        self._activer_2fa()
        self.assertNotIn("password_change_token", self._login().data["data"])

        session = self.client.post(
            "/api/auth/etudiant/totp/verify/",
            {"user_id": str(self.user.pk), "totp_code": pyotp.TOTP(self.user.totp_secret).now()},
            format="json",
        ).data["data"]
        self.assertTrue(session["requires_password_change"])

        res = self._changer(session["password_change_token"])
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["data"], {})
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

    def test_mot_de_passe_oublie_leve_l_obligation(self):
        from apps.users.services.auth_service import CommonAuthService, _generate_password_reset_token

        result = CommonAuthService.reset_password(self.user.email, NOUVEAU, _generate_password_reset_token(self.user))
        self.assertTrue(result.success)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

    def test_changement_depuis_le_profil_leve_l_obligation(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(
            "/api/auth/password/change/",
            {"old_password": TEMPORAIRE, "new_password": NOUVEAU, "confirm_password": NOUVEAU},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

    def test_comptes_existants_non_concernes(self):
        User.objects.filter(pk=self.user.pk).update(must_change_password=False)
        etape1 = self._login().data["data"]
        self.assertNotIn("requires_password_change", etape1)
        self.assertNotIn("password_change_token", etape1)
