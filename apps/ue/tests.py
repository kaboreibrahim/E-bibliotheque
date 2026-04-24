from django.test import TestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.services import UEService


class UEServiceTests(TestCase):
    def setUp(self):
        self.service = UEService()
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L1,
        )
        self.niveau_l2 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L2,
        )
        self.specialite_l1 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l1,
        )
        self.specialite_l2 = Specialite.objects.create(
            name="Droit prive",
            niveau=self.niveau_l2,
        )
        self.specialite_alt_l2 = Specialite.objects.create(
            name="Droit public",
            niveau=self.niveau_l2,
        )

    def test_create_ue_links_specialites(self):
        ue = self.service.create_ue(
            code="ue-dr-civ-01",
            name="Droit civil",
            specialite_ids=[str(self.specialite_l1.pk), str(self.specialite_l2.pk)],
        )

        self.assertSetEqual(
            set(ue.specialites.values_list("id", flat=True)),
            {self.specialite_l1.pk, self.specialite_l2.pk},
        )

    def test_list_ues_can_filter_by_specialite(self):
        ue_prive = self.service.create_ue(
            code="UE-DR-001",
            name="UE privee",
            specialite_ids=[str(self.specialite_l2.pk)],
        )
        self.service.create_ue(
            code="UE-DR-002",
            name="UE publique",
            specialite_ids=[str(self.specialite_alt_l2.pk)],
        )

        returned_ids = set(
            self.service.list_ues(specialite_id=str(self.specialite_l2.pk)).values_list("id", flat=True)
        )

        self.assertSetEqual(returned_ids, {ue_prive.pk})
