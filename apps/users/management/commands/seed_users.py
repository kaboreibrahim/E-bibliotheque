"""
=============================================================================
 Commande de seed : crée tous les types d'utilisateurs avec leurs niveaux.

 Usage :
   python manage.py seed_users
   python manage.py seed_users --reset   (supprime et recrée)
=============================================================================
"""

import pyotp
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.users.models.user_models import User
from apps.users.models.bibliothecaire_models import Bibliothecaire
from apps.users.models.etudiant_models import Etudiant
from apps.users.models.personne_models import PersonneExterne, EnseignantChercheur, Chercheur


# ---------------------------------------------------------------------------
# Données de seed
# ---------------------------------------------------------------------------

FILIERES_ET_NIVEAUX = [
    ("Droit", ["L1", "L2", "L3", "M1", "M2"]),
]

# Spécialités Droit par niveau (niveau_name → nom_specialite)
SPECIALITES_DROIT = {
    "L1": "Introduction au Droit",
    "L2": "Droit Civil et Droit des Obligations",
    "L3": "Droit des Affaires",
    "M1": "Droit des Contentieux",
    "M2": "Master Droits de l'Homme et Bonne Gouvernance",
}

ADMINISTRATEURS = [
    {
        "first_name": "Admin",
        "last_name": "Principal",
        "email": "admin@biblio.ci",
        "phone": "+2250700000001",
        "password": "Admin@2025!",
        "date_of_birth": date(1980, 1, 15),
    },
]

BIBLIOTHECAIRES = [
    {
        "first_name": "Kouamé",
        "last_name": "Assi",
        "email": "bibliothecaire1@biblio.ci",
        "phone": "+2250700000010",
        "password": "Biblio@2025!",
        "date_of_birth": date(1985, 3, 20),
        "badge_number": "BIB-001",
        "date_prise_poste": date(2020, 9, 1),
        "peut_gerer_documents": True,
        "peut_gerer_utilisateurs": False,
    },
    {
        "first_name": "Adjoua",
        "last_name": "Konan",
        "email": "bibliothecaire2@biblio.ci",
        "phone": "+2250700000011",
        "password": "Biblio@2025!",
        "date_of_birth": date(1990, 7, 5),
        "badge_number": "BIB-002",
        "date_prise_poste": date(2022, 1, 10),
        "peut_gerer_documents": True,
        "peut_gerer_utilisateurs": True,
    },
]

ETUDIANTS = [
    {
        "first_name": "Kouamé",
        "last_name": "Assoumou",
        "email": "etudiant.droit.l1@biblio.ci",
        "phone": "+2250700000020",
        "password": "Etudiant@2025!",
        "date_of_birth": date(2004, 3, 10),
        "filiere": "Droit",
        "niveau": "L1",
        "specialite": "Introduction au Droit",
        "activer": True,
    },
    {
        "first_name": "Awa",
        "last_name": "Traoré",
        "email": "etudiant.droit.l2@biblio.ci",
        "phone": "+2250700000021",
        "password": "Etudiant@2025!",
        "date_of_birth": date(2003, 7, 22),
        "filiere": "Droit",
        "niveau": "L2",
        "specialite": "Droit Civil et Droit des Obligations",
        "activer": True,
    },
    {
        "first_name": "Serge",
        "last_name": "Bléhi",
        "email": "etudiant.droit.l3@biblio.ci",
        "phone": "+2250700000022",
        "password": "Etudiant@2025!",
        "date_of_birth": date(2002, 1, 5),
        "filiere": "Droit",
        "niveau": "L3",
        "specialite": "Droit des Affaires",
        "activer": True,
    },
    {
        "first_name": "Fatou",
        "last_name": "Diallo",
        "email": "etudiant.droit.m1@biblio.ci",
        "phone": "+2250700000023",
        "password": "Etudiant@2025!",
        "date_of_birth": date(2000, 9, 14),
        "filiere": "Droit",
        "niveau": "M1",
        "specialite": "Droit des Contentieux",
        "activer": False,
    },
    {
        "first_name": "Dramane",
        "last_name": "Coulibaly",
        "email": "etudiant.droit.m2@biblio.ci",
        "phone": "+2250700000024",
        "password": "Etudiant@2025!",
        "date_of_birth": date(1999, 6, 30),
        "filiere": "Droit",
        "niveau": "M2",
        "specialite": "Master Droits de l'Homme et Bonne Gouvernance",
        "activer": True,
        "date_debut_validite": date.today(),
        "date_fin_validite": date.today() + timedelta(days=365),
    },
]

PERSONNES_EXTERNES = [
    {
        "first_name": "Jean-Baptiste",
        "last_name": "Kouassi",
        "email": "externe1@biblio.ci",
        "phone": "+2250700000030",
        "password": "Externe@2025!",
        "date_of_birth": date(1975, 4, 18),
        "numero_piece": "CI-2025-001234",
        "profession": "Avocat",
        "lieu_habitation": "Abidjan, Cocody",
        "date_debut_validite": date.today(),
        "date_fin_validite": date.today() + timedelta(days=180),
    },
    {
        "first_name": "Marie",
        "last_name": "N'Dri",
        "email": "externe2@biblio.ci",
        "phone": "+2250700000031",
        "password": "Externe@2025!",
        "date_of_birth": date(1988, 9, 9),
        "numero_piece": "CI-2025-005678",
        "profession": "Journaliste",
        "lieu_habitation": "Abidjan, Plateau",
    },
]

ENSEIGNANTS_CHERCHEURS = [
    {
        "first_name": "Pr. Lucien",
        "last_name": "Gnangui",
        "email": "enseignant1@biblio.ci",
        "phone": "+2250700000040",
        "password": "Enseignant@2025!",
        "date_of_birth": date(1970, 12, 1),
        "numero_piece": "CI-1995-111222",
        "lieu_habitation": "Abidjan, Marcory",
        "annee_service": 2000,
        "specialite_enseignee": "Intelligence Artificielle",
    },
    {
        "first_name": "Dr. Amlan",
        "last_name": "Kra",
        "email": "enseignant2@biblio.ci",
        "phone": "+2250700000041",
        "password": "Enseignant@2025!",
        "date_of_birth": date(1978, 3, 22),
        "numero_piece": "CI-2005-333444",
        "lieu_habitation": "Abidjan, Yopougon",
        "annee_service": 2010,
        "specialite_enseignee": "Droit constitutionnel",
    },
]

CHERCHEURS = [
    {
        "first_name": "Rodrigue",
        "last_name": "Akaffou",
        "email": "chercheur1@biblio.ci",
        "phone": "+2250700000050",
        "password": "Chercheur@2025!",
        "date_of_birth": date(1982, 7, 7),
        "numero_piece": "CI-2010-555666",
        "lieu_habitation": "Abidjan, Deux-Plateaux",
        "annee_service": 2015,
        "specialite_enseignee": "Bioinformatique",
    },
    {
        "first_name": "Sandrine",
        "last_name": "Tah",
        "email": "chercheur2@biblio.ci",
        "phone": "+2250700000051",
        "password": "Chercheur@2025!",
        "date_of_birth": date(1990, 1, 17),
        "numero_piece": "CI-2018-777888",
        "lieu_habitation": "Abidjan, Riviera",
        "annee_service": 2020,
        "specialite_enseignee": "Mathématiques appliquées",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_totp(email: str) -> tuple[str, str]:
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=email, issuer_name="Bibliothèque Universitaire CI"
    )
    return secret, uri


def _create_user(email, password, first_name, last_name, phone,
                 user_type, date_of_birth=None, is_active=True, is_staff=False) -> User:
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        user_type=user_type,
        date_of_birth=date_of_birth,
        is_active=is_active,
        is_staff=is_staff,
    )
    user.set_password(password)
    secret, _ = _generate_totp(email)
    user.totp_secret = secret
    user.save()
    return user


# ---------------------------------------------------------------------------
# Commande
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Peuple la base avec tous les types d'utilisateurs et les niveaux."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les données existantes avant de recréer.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        with transaction.atomic():
            filieres, niveaux = self._seed_filieres_et_niveaux()
            self._seed_administrateurs()
            self._seed_bibliothecaires()
            self._seed_etudiants(niveaux)
            self._seed_personnes_externes()
            self._seed_enseignants_chercheurs()
            self._seed_chercheurs()

        self.stdout.write(self.style.SUCCESS("\n✅  Seed terminé avec succès.\n"))
        self._print_summary()

    # ── Reset ────────────────────────────────────────────────────────────────

    def _reset(self):
        self.stdout.write(self.style.WARNING("⚠️  Suppression des données existantes…"))
        emails = (
            [a["email"] for a in ADMINISTRATEURS]
            + [b["email"] for b in BIBLIOTHECAIRES]
            + [e["email"] for e in ETUDIANTS]
            + [p["email"] for p in PERSONNES_EXTERNES]
            + [ec["email"] for ec in ENSEIGNANTS_CHERCHEURS]
            + [c["email"] for c in CHERCHEURS]
        )
        deleted, _ = User.objects.filter(email__in=emails).delete()
        self.stdout.write(f"   {deleted} utilisateur(s) supprimé(s).")

    # ── Filières & Niveaux ───────────────────────────────────────────────────

    def _seed_filieres_et_niveaux(self):
        self.stdout.write("\n📚  Filières & Niveaux & Spécialités")
        filieres = {}
        niveaux = {}

        for nom_filiere, liste_niveaux in FILIERES_ET_NIVEAUX:
            filiere, created = Filiere.objects.get_or_create(name=nom_filiere)
            filieres[nom_filiere] = filiere
            status = "créée" if created else "existante"
            self.stdout.write(f"   Filière {filiere.name} — {status}")

            for code_niveau in liste_niveaux:
                niveau, n_created = Niveau.objects.get_or_create(
                    filiere=filiere, name=code_niveau
                )
                niveaux[(nom_filiere, code_niveau)] = niveau
                n_status = "créé" if n_created else "existant"
                self.stdout.write(f"      └─ {code_niveau} — {n_status}")

                # Créer la spécialité Droit liée à ce niveau
                nom_spe = SPECIALITES_DROIT.get(code_niveau)
                if nom_spe:
                    spe, s_created = Specialite.objects.get_or_create(
                        name=nom_spe, niveau=niveau
                    )
                    s_status = "créée" if s_created else "existante"
                    self.stdout.write(f"         └─ Spécialité : {spe.name} — {s_status}")

        return filieres, niveaux

    # ── Administrateurs ──────────────────────────────────────────────────────

    def _seed_administrateurs(self):
        self.stdout.write("\n🔐  Administrateurs")
        for data in ADMINISTRATEURS:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue
            _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.ADMINISTRATEUR,
                date_of_birth=data.get("date_of_birth"),
                is_active=True,
                is_staff=True,
            )
            self.stdout.write(self.style.SUCCESS(f"   ✓ Admin {data['email']}"))

    # ── Bibliothécaires ──────────────────────────────────────────────────────

    def _seed_bibliothecaires(self):
        self.stdout.write("\n📖  Bibliothécaires")
        for data in BIBLIOTHECAIRES:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue
            user = _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.BIBLIOTHECAIRE,
                date_of_birth=data.get("date_of_birth"),
                is_active=True,
                is_staff=True,
            )
            Bibliothecaire.objects.create(
                user=user,
                badge_number=data.get("badge_number"),
                date_prise_poste=data.get("date_prise_poste"),
                peut_gerer_documents=data.get("peut_gerer_documents", True),
                peut_gerer_utilisateurs=data.get("peut_gerer_utilisateurs", False),
            )
            self.stdout.write(self.style.SUCCESS(f"   ✓ Bibliothécaire {data['email']}"))

    # ── Étudiants ────────────────────────────────────────────────────────────

    def _seed_etudiants(self, niveaux: dict):
        self.stdout.write("\n🎓  Étudiants")
        for data in ETUDIANTS:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue

            niveau = niveaux.get((data["filiere"], data["niveau"]))
            if not niveau:
                self.stdout.write(
                    self.style.ERROR(
                        f"   [ERREUR] Niveau {data['niveau']} / {data['filiere']} introuvable."
                    )
                )
                continue

            # Récupérer la spécialité
            specialite = None
            nom_spe = data.get("specialite")
            if nom_spe:
                try:
                    specialite = Specialite.objects.get(name=nom_spe, niveau=niveau)
                except Specialite.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"   [ERREUR] Spécialité '{nom_spe}' introuvable pour {data['niveau']}."
                        )
                    )
                    continue

            user = _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.ETUDIANT,
                date_of_birth=data.get("date_of_birth"),
                is_active=False,
            )

            etudiant = Etudiant(
                user=user,
                filiere=niveau.filiere,
                niveau=niveau,
                specialite=specialite,
                annee_inscription=timezone.now().year,
                date_debut_validite=data.get("date_debut_validite"),
                date_fin_validite=data.get("date_fin_validite"),
            )
            etudiant.save()

            if data.get("activer"):
                etudiant.activer_compte()

            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ Étudiant {data['email']} | {data['filiere']} {data['niveau']}"
                    f" | {etudiant.statut_compte}"
                )
            )

    # ── Personnes externes ───────────────────────────────────────────────────

    def _seed_personnes_externes(self):
        self.stdout.write("\n🌐  Personnes externes")
        for data in PERSONNES_EXTERNES:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue
            user = _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.PERSONNE_EXTERNE,
                date_of_birth=data.get("date_of_birth"),
                is_active=True,
            )
            personne = PersonneExterne(
                user=user,
                numero_piece=data.get("numero_piece", ""),
                profession=data.get("profession", ""),
                lieu_habitation=data.get("lieu_habitation", ""),
                date_debut_validite=data.get("date_debut_validite"),
                date_fin_validite=data.get("date_fin_validite"),
            )
            if data.get("date_debut_validite") and data.get("date_fin_validite"):
                personne.compte_active_le = timezone.now()
            personne.save()
            self.stdout.write(self.style.SUCCESS(f"   ✓ Personne externe {data['email']}"))

    # ── Enseignants-Chercheurs ───────────────────────────────────────────────

    def _seed_enseignants_chercheurs(self):
        self.stdout.write("\n👨‍🏫  Enseignants-Chercheurs")
        for data in ENSEIGNANTS_CHERCHEURS:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue
            user = _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.ENSEIGNANT_CHERCHEUR,
                date_of_birth=data.get("date_of_birth"),
                is_active=True,
            )
            EnseignantChercheur.objects.create(
                user=user,
                numero_piece=data.get("numero_piece", ""),
                lieu_habitation=data.get("lieu_habitation", ""),
                annee_service=data.get("annee_service"),
                specialite_enseignee=data.get("specialite_enseignee", ""),
            )
            self.stdout.write(self.style.SUCCESS(f"   ✓ Enseignant-Chercheur {data['email']}"))

    # ── Chercheurs ───────────────────────────────────────────────────────────

    def _seed_chercheurs(self):
        self.stdout.write("\n🔬  Chercheurs")
        for data in CHERCHEURS:
            if User.objects.filter(email=data["email"]).exists():
                self.stdout.write(f"   [SKIP] {data['email']} existe déjà.")
                continue
            user = _create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.CHERCHEUR,
                date_of_birth=data.get("date_of_birth"),
                is_active=True,
            )
            Chercheur.objects.create(
                user=user,
                numero_piece=data.get("numero_piece", ""),
                lieu_habitation=data.get("lieu_habitation", ""),
                annee_service=data.get("annee_service"),
                specialite_enseignee=data.get("specialite_enseignee", ""),
            )
            self.stdout.write(self.style.SUCCESS(f"   ✓ Chercheur {data['email']}"))

    # ── Résumé ───────────────────────────────────────────────────────────────

    def _print_summary(self):
        self.stdout.write("─" * 60)
        self.stdout.write("COMPTES CRÉÉS — récapitulatif des accès")
        self.stdout.write("─" * 60)

        groups = [
            ("Administrateur",      ADMINISTRATEURS),
            ("Bibliothécaire",      BIBLIOTHECAIRES),
            ("Étudiant",            ETUDIANTS),
            ("Personne externe",    PERSONNES_EXTERNES),
            ("Enseignant-Chercheur",ENSEIGNANTS_CHERCHEURS),
            ("Chercheur",           CHERCHEURS),
        ]
        for label, items in groups:
            self.stdout.write(f"\n  {label}s :")
            for item in items:
                self.stdout.write(f"    email    : {item['email']}")
                self.stdout.write(f"    password : {item['password']}")
                self.stdout.write("")
        self.stdout.write("─" * 60)
        self.stdout.write(
            "⚠️  Le 2FA (TOTP) est généré mais non confirmé.\n"
            "   Chaque utilisateur devra configurer Google Authenticator\n"
            "   lors de sa première connexion via /api/auth/totp/setup/\n"
        )
