from datetime import timedelta
from types import SimpleNamespace
import uuid

from django.test import TestCase
from django.utils import timezone

from apps.history.models import HistoriqueAction, HistoriqueActionService
from apps.users.models import User


class HistoriqueActionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="history@example.com",
            password="Secret123!",
            phone="+2250102030405",
            first_name="History",
            last_name="Tester",
        )

    def test_log_connexion_is_saved_in_postgresql(self):
        log_id = HistoriqueActionService.log_connexion(
            user=self.user,
            statut=HistoriqueAction.Statut.SUCCES,
            ip="127.0.0.1",
            ua="pytest-agent",
        )

        log = HistoriqueAction.objects.get(pk=log_id)

        self.assertEqual(log.action, HistoriqueAction.Action.CONNEXION)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.user_email, self.user.email)
        self.assertEqual(log.details["email"], self.user.email)
        self.assertEqual(log.ip_address, "127.0.0.1")

    def test_specialized_helpers_store_business_details(self):
        document = SimpleNamespace(
            id=uuid.uuid4(),
            title="Cours de droit",
            type="COURS",
        )
        etudiant = SimpleNamespace(
            id=uuid.uuid4(),
            user=self.user,
        )
        favori = SimpleNamespace(
            id=uuid.uuid4(),
            etudiant=etudiant,
            document=document,
        )
        consultation = SimpleNamespace(
            id=uuid.uuid4(),
            type_consultation="VUE",
            document=document,
            recherche_query="procedure civile",
            duree_secondes=42,
        )

        HistoriqueActionService.log_favori(
            "AJOUT",
            user=self.user,
            favori=favori,
        )
        HistoriqueActionService.log_consultation(
            "TERMINEE",
            user=self.user,
            consultation=consultation,
            details={"fin_consultation": "2026-04-03T12:00:00Z"},
        )

        favori_log = HistoriqueAction.objects.get(action=HistoriqueAction.Action.FAVORI_AJOUT)
        consultation_log = HistoriqueAction.objects.get(
            action=HistoriqueAction.Action.CONSULTATION_TERMINEE
        )

        self.assertEqual(favori_log.details["document_titre"], "Cours de droit")
        self.assertEqual(favori_log.details["etudiant_email"], self.user.email)
        self.assertEqual(consultation_log.details["duree_secondes"], 42)
        self.assertEqual(
            consultation_log.details["fin_consultation"],
            "2026-04-03T12:00:00Z",
        )

    def test_get_echecs_recents_filters_old_failures(self):
        old_log = HistoriqueAction.objects.create(
            action=HistoriqueAction.Action.CONNEXION_ECHEC,
            user=self.user,
            user_email=self.user.email,
            user_type=self.user.user_type,
            statut=HistoriqueAction.Statut.ECHEC,
            details={},
        )
        HistoriqueAction.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(minutes=90)
        )

        HistoriqueActionService.log_connexion(
            user=self.user,
            statut=HistoriqueAction.Statut.ECHEC,
        )

        logs = HistoriqueActionService.get_echecs_recents(minutes=30)
        returned_ids = {item["id"] for item in logs}

        self.assertEqual(len(logs), 1)
        self.assertNotIn(str(old_log.pk), returned_ids)
