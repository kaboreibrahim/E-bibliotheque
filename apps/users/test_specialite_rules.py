from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant, User


class EtudiantSpecialiteRulesTests(TestCase):
    def setUp(self):
        self.filiere = Filiere.objects.create(name="Droit")
        self.niveau_l1 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L1)
        self.niveau_l3 = Niveau.objects.create(filiere=self.filiere, name=Niveau.NiveauChoices.L3)
        self.specialite_l1 = Specialite.objects.create(name="Carriere judiciaire L1", niveau=self.niveau_l1)

    def _create_user(self, suffix: str) -> User:
        return User.objects.create_user(
            email=f"etu-{suffix}@example.com",
            password="Password123!",
            first_name="Awa",
            last_name="KONE",
            phone=f"+2250700000{suffix}",
            user_type=User.UserType.ETUDIANT,
        )

    def test_requires_specialite_for_l1_students(self):
        user = self._create_user("001")

        with self.assertRaises(ValidationError) as ctx:
            Etudiant.objects.create(
                user=user,
                filiere=self.filiere,
                niveau=self.niveau_l1,
                specialite=None,
                annee_inscription=2026,
            )

        self.assertIn("specialite", ctx.exception.message_dict)

    def test_allows_l1_student_with_matching_specialite(self):
        user = self._create_user("002")

        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau_l1,
            specialite=self.specialite_l1,
            annee_inscription=2026,
        )

        self.assertEqual(etudiant.specialite, self.specialite_l1)

    def test_requires_specialite_for_l3_students(self):
        user = self._create_user("003")

        with self.assertRaises(ValidationError) as ctx:
            Etudiant.objects.create(
                user=user,
                filiere=self.filiere,
                niveau=self.niveau_l3,
                specialite=None,
                annee_inscription=2026,
            )

        self.assertIn("specialite", ctx.exception.message_dict)

    def test_allows_l3_student_with_matching_specialite(self):
        user = self._create_user("004")
        specialite_l3 = Specialite.objects.create(name="Carriere judiciaire L3", niveau=self.niveau_l3)

        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau_l3,
            specialite=specialite_l3,
            annee_inscription=2026,
        )

        self.assertEqual(etudiant.specialite, specialite_l3)
