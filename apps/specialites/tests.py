from django.test import TestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite


class SpecialiteRulesTests(TestCase):
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.niveau_l2 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L2)
        self.niveau_l3 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L3)

    def test_allows_specialites_for_l1_and_l2(self):
        specialite_l1 = Specialite.objects.create(name="Droit des affaires L1", niveau=self.niveau_l1)
        specialite_l2 = Specialite.objects.create(name="Droit des affaires L2", niveau=self.niveau_l2)

        self.assertEqual(specialite_l1.niveau, self.niveau_l1)
        self.assertEqual(specialite_l2.niveau, self.niveau_l2)

    def test_allows_specialite_for_l3(self):
        specialite = Specialite.objects.create(name="Droit general L3", niveau=self.niveau_l3)

        self.assertEqual(specialite.niveau, self.niveau_l3)
