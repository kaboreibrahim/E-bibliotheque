from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models import Etudiant
from apps.users.serializers import StudentRegistrationSerializer

User = get_user_model()


class UserTestDataMixin:
    def setUp(self):
        super().setUp()
        self.filiere = Filiere.objects.create(name='Informatique')
        self.niveau_l1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.L1,
        )
        self.niveau_m1 = Niveau.objects.create(
            filiere=self.filiere,
            name=Niveau.NiveauChoices.M1,
        )
        self.specialite_m1 = Specialite.objects.create(
            name='Intelligence Artificielle',
            niveau=self.niveau_m1,
        )

    def student_payload(self, **overrides):
        payload = {
            'email': 'etudiant@example.com',
            'password': 'Password123',
            'password_confirmation': 'Password123',
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'phone': '+2250102030405',
            'filiere': self.filiere.id,
            'niveau': self.niveau_m1.id,
            'specialite': self.specialite_m1.id,
            'annee_inscription': 2026,
        }
        payload.update(overrides)
        return payload

    def create_student_user(self, **overrides):
        user = User.objects.create_user(
            email=overrides.pop('email', 'student-login@example.com'),
            password=overrides.pop('password', 'Password123'),
            first_name=overrides.pop('first_name', 'Alan'),
            last_name=overrides.pop('last_name', 'Turing'),
            phone=overrides.pop('phone', '+2250607080910'),
            user_type=User.UserType.ETUDIANT,
            **overrides,
        )
        etudiant = Etudiant.objects.create(
            user=user,
            filiere=self.filiere,
            niveau=self.niveau_m1,
            specialite=self.specialite_m1,
            annee_inscription=2026,
        )
        return user, etudiant


class StudentRegistrationSerializerTests(UserTestDataMixin, TestCase):
    def test_requires_specialite_for_master_levels(self):
        serializer = StudentRegistrationSerializer(
            data=self.student_payload(specialite=None)
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('specialite', serializer.errors)

    def test_rejects_specialite_for_tronc_commun(self):
        serializer = StudentRegistrationSerializer(
            data=self.student_payload(
                niveau=self.niveau_l1.id,
                specialite=self.specialite_m1.id,
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('specialite', serializer.errors)

    def test_accepts_valid_master_student_payload(self):
        serializer = StudentRegistrationSerializer(data=self.student_payload())

        self.assertTrue(serializer.is_valid(), serializer.errors)


class UserApiTests(UserTestDataMixin, APITestCase):
    def test_register_student_creates_profile_and_returns_nested_student(self):
        response = self.client.post(
            '/users/auth/register/etudiant/',
            self.student_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Etudiant.objects.count(), 1)
        self.assertEqual(response.data['email'], 'etudiant@example.com')
        self.assertEqual(
            response.data['profil_etudiant']['specialite']['name'],
            self.specialite_m1.name,
        )
        self.assertTrue(response.data['profil_etudiant']['matricule'])

    def test_token_endpoint_accepts_student_matricule(self):
        user, etudiant = self.create_student_user()

        response = self.client.post(
            '/users/auth/token/',
            {
                'login': etudiant.matricule,
                'password': 'Password123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['email'], user.email)
        self.assertEqual(response.data['user']['matricule'], etudiant.matricule)

    def test_me_endpoint_returns_authenticated_user(self):
        user, etudiant = self.create_student_user()
        self.client.force_authenticate(user=user)

        response = self.client.get('/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)
        self.assertEqual(response.data['matricule'], etudiant.matricule)

    def test_user_list_requires_admin(self):
        user, _ = self.create_student_user()
        self.client.force_authenticate(user=user)

        response = self.client.get('/users/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_list_allows_admin(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='Password123',
            first_name='Grace',
            last_name='Hopper',
            phone='+2251112131415',
        )
        self.client.force_authenticate(user=admin)

        response = self.client.get('/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], admin.email)
