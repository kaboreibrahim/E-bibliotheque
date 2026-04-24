"""
Seed script for the E-BIBLIO project.

Usage:
    python seed_database.py
    env\\Scripts\\python.exe seed_database.py

The script is safe to run multiple times. Existing rows are updated instead of
being duplicated when possible.
"""

from __future__ import annotations

import argparse
import base64
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import django
from django.utils import timezone


ADMIN_PASSWORD = "Admin12345!"
BIBLIOTHECAIRE_PASSWORD = "Biblio12345!"
ETUDIANT_PASSWORD = "Etudiant12345!"
ANNEE_INSCRIPTION = date.today().year
ANNEE_ACADEMIQUE_DEBUT = max(ANNEE_INSCRIPTION - 1, 2025)

FILIERE_SEEDS = {
    "Informatique": {
        "L1": "Programmation et algorithmique",
        "L2": "Developpement web",
        "L3": "Genie logiciel",
        "M1": "Intelligence artificielle",
        "M2": "Cybersecurite",
    },
    "Droit": {
        "L1": "Fondements du droit",
        "M1": "Droit des affaires",
        "M2": "Contentieux",
        "DOCTORAT": "Recherche doctorale en droit",
    },
}

BIBLIOTHECAIRE_SEEDS = [
    {
        "email": "biblio.principal@ebiblio.local",
        "first_name": "Nadia",
        "last_name": "Kone",
        "phone": "+2250700000002",
        "badge_number": "BIB-001",
        "peut_gerer_documents": True,
        "peut_gerer_utilisateurs": True,
    },
    {
        "email": "biblio.support@ebiblio.local",
        "first_name": "Moussa",
        "last_name": "Traore",
        "phone": "+2250700000003",
        "badge_number": "BIB-002",
        "peut_gerer_documents": True,
        "peut_gerer_utilisateurs": False,
    },
]

ETUDIANT_SEEDS = [
    {
        "email": "etu.info.l1@ebiblio.local",
        "first_name": "Awa",
        "last_name": "Diallo",
        "phone": "+2250700000011",
        "filiere": "Informatique",
        "niveau": "L1",
        "active_days_ago": 5,
    },
    {
        "email": "etu.info.l3@ebiblio.local",
        "first_name": "Kevin",
        "last_name": "Yao",
        "phone": "+2250700000012",
        "filiere": "Informatique",
        "niveau": "L3",
        "active_days_ago": 4,
    },
    {
        "email": "etu.info.m2@ebiblio.local",
        "first_name": "Ruth",
        "last_name": "Bamba",
        "phone": "+2250700000013",
        "filiere": "Informatique",
        "niveau": "M2",
        "active_days_ago": 3,
    },
    {
        "email": "etu.droit.l1@ebiblio.local",
        "first_name": "Junior",
        "last_name": "Kouassi",
        "phone": "+2250700000014",
        "filiere": "Droit",
        "niveau": "L1",
        "active_days_ago": 6,
    },
    {
        "email": "etu.droit.m2@ebiblio.local",
        "first_name": "Fatou",
        "last_name": "Coulibaly",
        "phone": "+2250700000015",
        "filiere": "Droit",
        "niveau": "M2",
        "active_days_ago": 2,
    },
    {
        "email": "doctorant@ebiblio.local",
        "first_name": "Armand",
        "last_name": "Nguessan",
        "phone": "+2250700000016",
        "filiere": "Droit",
        "niveau": "DOCTORAT",
        "active_days_ago": 1,
    },
]

UE_SEEDS = [
    {
        "code": "INF101",
        "name": "Algorithmique et Python",
        "filiere": "Informatique",
        "niveaux": ["L1"],
        "ecues": [
            {"code": "INF101-1", "name": "Bases de l algorithmique", "coef": Decimal("3.00")},
            {"code": "INF101-2", "name": "Python debutant", "coef": Decimal("2.00")},
        ],
    },
    {
        "code": "INF301",
        "name": "APIs et genie logiciel",
        "filiere": "Informatique",
        "niveaux": ["L3"],
        "ecues": [
            {"code": "INF301-1", "name": "Conception d API REST", "coef": Decimal("3.00")},
            {"code": "INF301-2", "name": "Tests et qualite logicielle", "coef": Decimal("2.00")},
        ],
    },
    {
        "code": "INF501",
        "name": "Securite avancee",
        "filiere": "Informatique",
        "niveaux": ["M2"],
        "ecues": [
            {"code": "INF501-1", "name": "Securite des applications web", "coef": Decimal("4.00")},
        ],
    },
    {
        "code": "DRT101",
        "name": "Introduction au droit",
        "filiere": "Droit",
        "niveaux": ["L1"],
        "ecues": [
            {"code": "DRT101-1", "name": "Institutions judiciaires", "coef": Decimal("3.00")},
        ],
    },
    {
        "code": "DRT501",
        "name": "Procedure contentieuse",
        "filiere": "Droit",
        "niveaux": ["M2"],
        "ecues": [
            {"code": "DRT501-1", "name": "Procedure civile approfondie", "coef": Decimal("4.00")},
        ],
    },
]

DOCUMENT_SEEDS = [
    {
        "title": "Cours - Python pour debutants",
        "type": "COURS",
        "filiere": "Informatique",
        "niveau": "L1",
        "ecue_code": "INF101-2",
        "encadreur": "Mme Kone",
        "ajoute_par": "biblio.principal@ebiblio.local",
    },
    {
        "title": "Examen - API REST et tests",
        "type": "EXAMEN",
        "filiere": "Informatique",
        "niveau": "L3",
        "ecue_code": "INF301-1",
        "encadreur": "M. Traore",
        "ajoute_par": "biblio.principal@ebiblio.local",
    },
    {
        "title": "Cours - Securite des applications web",
        "type": "COURS",
        "filiere": "Informatique",
        "niveau": "M2",
        "ecue_code": "INF501-1",
        "encadreur": "Dr. Bamba",
        "ajoute_par": "biblio.support@ebiblio.local",
    },
    {
        "title": "Memoire - Detection de fraudes par IA",
        "type": "MEMOIRE",
        "filiere": "Informatique",
        "niveau": "M1",
        "auteur": "Kouame Serge",
        "encadreur": "Pr. Yao",
        "ajoute_par": "biblio.principal@ebiblio.local",
    },
    {
        "title": "Cours - Introduction au droit prive",
        "type": "COURS",
        "filiere": "Droit",
        "niveau": "L1",
        "ecue_code": "DRT101-1",
        "encadreur": "Pr. Ahoua",
        "ajoute_par": "biblio.support@ebiblio.local",
    },
    {
        "title": "Memoire - Arbitrage et contentieux commercial",
        "type": "MEMOIRE",
        "filiere": "Droit",
        "niveau": "M2",
        "ecue_code": "DRT501-1",
        "auteur": "Coulibaly Fatou",
        "encadreur": "Pr. Nguessan",
        "ajoute_par": "biblio.principal@ebiblio.local",
    },
    {
        "title": "These - Modernisation de la justice numerique",
        "type": "THESE",
        "filiere": "Droit",
        "niveau": "DOCTORAT",
        "auteur": "Armand Nguessan",
        "encadreur": "Pr. Koffi",
        "ajoute_par": "biblio.principal@ebiblio.local",
    },
]

CONSULTATION_SEEDS = [
    {
        "email": "etu.info.l1@ebiblio.local",
        "document": "Cours - Python pour debutants",
        "duration_seconds": 420,
        "favorite": True,
        "days_ago": 4,
    },
    {
        "email": "etu.info.l3@ebiblio.local",
        "document": "Examen - API REST et tests",
        "duration_seconds": 300,
        "favorite": True,
        "days_ago": 3,
    },
    {
        "email": "etu.info.m2@ebiblio.local",
        "document": "Cours - Securite des applications web",
        "duration_seconds": 540,
        "favorite": False,
        "days_ago": 2,
    },
    {
        "email": "etu.droit.m2@ebiblio.local",
        "document": "Memoire - Arbitrage et contentieux commercial",
        "duration_seconds": 660,
        "favorite": True,
        "days_ago": 1,
    },
    {
        "email": "doctorant@ebiblio.local",
        "document": "These - Modernisation de la justice numerique",
        "duration_seconds": 900,
        "favorite": True,
        "days_ago": 1,
    },
]

SEARCH_SEEDS = [
    {"email": "etu.info.l1@ebiblio.local", "query": "python django debutant", "days_ago": 4},
    {"email": "etu.info.m2@ebiblio.local", "query": "cybersecurite applications web", "days_ago": 2},
    {"email": "etu.droit.m2@ebiblio.local", "query": "contentieux commercial arbitrage", "days_ago": 1},
]


def bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def get_all_manager(model):
    return getattr(model, "all_objects", model.objects)


def revive_soft_deleted(instance) -> None:
    if getattr(instance, "deleted", None):
        instance.deleted = None
        if hasattr(instance, "deleted_by_cascade"):
            instance.deleted_by_cascade = False


def upsert_instance(model, lookup: dict, values: dict | None = None, *, validate: bool = True):
    values = values or {}
    manager = get_all_manager(model)
    instance = manager.filter(**lookup).order_by("pk").first()
    created = instance is None

    if created:
        instance = model(**lookup)

    revive_soft_deleted(instance)

    for field_name, value in values.items():
        setattr(instance, field_name, value)

    if validate and hasattr(instance, "full_clean"):
        instance.full_clean()

    instance.save()
    return instance, created


def upsert_user(*, email: str, password: str, **values):
    from apps.users.models import User

    manager = get_all_manager(User)
    user = manager.filter(email=email).order_by("pk").first()
    created = user is None

    if created:
        user = User(email=email)

    revive_soft_deleted(user)
    user.email = email

    for field_name, value in values.items():
        setattr(user, field_name, value)

    user.set_password(password)
    user.full_clean()
    user.save()
    return user, created


def build_seed_file_base64(title: str, document_type: str) -> str:
    content = (
        f"E-BIBLIO seed document\n"
        f"Type: {document_type}\n"
        f"Titre: {title}\n"
        f"Annee academique: {ANNEE_ACADEMIQUE_DEBUT}-{ANNEE_ACADEMIQUE_DEBUT + 1}\n"
    ).encode("utf-8")
    return base64.b64encode(content).decode("ascii")


def seed_reference_time():
    return timezone.make_aware(
        datetime(2026, 1, 15, 10, 0, 0),
        timezone.get_current_timezone(),
    )


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def seed_catalog(summary: dict) -> dict:
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau
    from apps.specialites.models import Specialite
    from apps.ue.models import ECUE, UE

    context = {
        "filieres": {},
        "niveaux": {},
        "specialites": {},
        "ues": {},
        "ecues": {},
    }

    print_section("Filieres, niveaux et specialites")
    for filiere_name, niveaux in FILIERE_SEEDS.items():
        filiere, created = upsert_instance(Filiere, {"name": filiere_name})
        summary["filieres"] += int(created)
        context["filieres"][filiere_name] = filiere

        for niveau_name, specialite_name in niveaux.items():
            niveau, niveau_created = upsert_instance(
                Niveau,
                {"filiere": filiere, "name": niveau_name},
            )
            summary["niveaux"] += int(niveau_created)
            context["niveaux"][(filiere_name, niveau_name)] = niveau

            specialite, specialite_created = upsert_instance(
                Specialite,
                {"niveau": niveau, "name": specialite_name},
            )
            summary["specialites"] += int(specialite_created)
            context["specialites"][(filiere_name, niveau_name)] = specialite

    print(f"Filieres preparees : {len(context['filieres'])}")
    print(f"Niveaux prepares : {len(context['niveaux'])}")
    print(f"Specialites preparees : {len(context['specialites'])}")

    print_section("UE et ECUE")
    for row in UE_SEEDS:
        ue, ue_created = upsert_instance(
            UE,
            {"code": row["code"]},
            {"name": row["name"], "coef": Decimal("0.00")},
        )
        summary["ues"] += int(ue_created)

        niveaux = [
            context["niveaux"][(row["filiere"], niveau_name)]
            for niveau_name in row["niveaux"]
        ]
        ue.niveaux.set(niveaux)
        ue.sync_coef_from_ecues()
        context["ues"][row["code"]] = ue

        for ecue_row in row["ecues"]:
            ecue, ecue_created = upsert_instance(
                ECUE,
                {"ue": ue, "code": ecue_row["code"]},
                {
                    "name": ecue_row["name"],
                    "coef": ecue_row["coef"],
                },
            )
            summary["ecues"] += int(ecue_created)
            context["ecues"][ecue_row["code"]] = ecue

        ue.sync_coef_from_ecues()

    print(f"UE preparees : {len(context['ues'])}")
    print(f"ECUE prepares : {len(context['ecues'])}")
    return context


def seed_users(context: dict, summary: dict) -> dict:
    from apps.users.models import Bibliothecaire, Etudiant, User

    users_by_email = {}
    profiles_by_email = {}

    print_section("Utilisateurs")
    admin, admin_created = upsert_user(
        email="admin@ebiblio.local",
        password=ADMIN_PASSWORD,
        first_name="Super",
        last_name="Admin",
        phone="+2250700000001",
        user_type=User.UserType.ADMINISTRATEUR,
        is_staff=True,
        is_superuser=True,
        is_active=True,
        is_2fa_enabled=True,
    )
    users_by_email[admin.email] = admin
    summary["users"] += int(admin_created)

    for row in BIBLIOTHECAIRE_SEEDS:
        user, user_created = upsert_user(
            email=row["email"],
            password=BIBLIOTHECAIRE_PASSWORD,
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            user_type=User.UserType.BIBLIOTHECAIRE,
            is_staff=True,
            is_superuser=False,
            is_active=True,
            is_2fa_enabled=True,
        )
        users_by_email[user.email] = user
        summary["users"] += int(user_created)

        profil, profil_created = upsert_instance(
            Bibliothecaire,
            {"user": user},
            {
                "badge_number": row["badge_number"],
                "date_prise_poste": date.today() - timedelta(days=120),
                "peut_gerer_documents": row["peut_gerer_documents"],
                "peut_gerer_utilisateurs": row["peut_gerer_utilisateurs"],
            },
        )
        profiles_by_email[user.email] = profil
        summary["bibliothecaires"] += int(profil_created)

    for row in ETUDIANT_SEEDS:
        user, user_created = upsert_user(
            email=row["email"],
            password=ETUDIANT_PASSWORD,
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            user_type=User.UserType.ETUDIANT,
            is_staff=False,
            is_superuser=False,
            is_active=True,
            is_2fa_enabled=False,
        )
        users_by_email[user.email] = user
        summary["users"] += int(user_created)

        filiere_name = row["filiere"]
        niveau_name = row["niveau"]
        profil, profil_created = upsert_instance(
            Etudiant,
            {"user": user},
            {
                "filiere": context["filieres"][filiere_name],
                "niveau": context["niveaux"][(filiere_name, niveau_name)],
                "specialite": context["specialites"][(filiere_name, niveau_name)],
                "annee_inscription": ANNEE_INSCRIPTION,
                "compte_active_le": timezone.now() - timedelta(days=row["active_days_ago"]),
                "nb_reactivations": 0,
                "derniere_reactivation_par": admin,
            },
        )
        profiles_by_email[user.email] = profil
        summary["etudiants"] += int(profil_created)

    print(f"Utilisateurs prepares : {len(users_by_email)}")
    print(f"Profils bibliothecaires : {len(BIBLIOTHECAIRE_SEEDS)}")
    print(f"Profils etudiants : {len(ETUDIANT_SEEDS)}")
    return {
        "users_by_email": users_by_email,
        "profiles_by_email": profiles_by_email,
    }


def seed_documents(context: dict, users_context: dict, summary: dict) -> dict:
    from apps.documents.models import Document

    documents_by_title = {}

    print_section("Documents")
    for row in DOCUMENT_SEEDS:
        filiere_name = row["filiere"]
        niveau_name = row["niveau"]
        ecue = context["ecues"].get(row.get("ecue_code"))
        document, created = upsert_instance(
            Document,
            {"title": row["title"]},
            {
                "type": row["type"],
                "filiere": context["filieres"][filiere_name],
                "niveau": context["niveaux"][(filiere_name, niveau_name)],
                "specialite": context["specialites"][(filiere_name, niveau_name)],
                "ue": ecue,
                "annee_academique_debut": ANNEE_ACADEMIQUE_DEBUT,
                "auteur": row.get("auteur", ""),
                "encadreur": row.get("encadreur", ""),
                "file_base64": build_seed_file_base64(row["title"], row["type"]),
                "file_name": "",
                "file_mime_type": "text/plain",
                "description": f"Document de demonstration pour {filiere_name} - {niveau_name}",
                "ajoute_par": users_context["users_by_email"][row["ajoute_par"]],
            },
        )
        documents_by_title[document.title] = document
        summary["documents"] += int(created)

    print(f"Documents prepares : {len(documents_by_title)}")
    return documents_by_title


def seed_activity(users_context: dict, documents_by_title: dict, summary: dict) -> None:
    from apps.consultations.models import Consultation
    from apps.favoris.models import Favori

    print_section("Consultations et favoris")
    reference_time = seed_reference_time()
    for row in CONSULTATION_SEEDS:
        user = users_context["users_by_email"][row["email"]]
        etudiant = users_context["profiles_by_email"][row["email"]]
        document = documents_by_title[row["document"]]
        debut = reference_time - timedelta(days=row["days_ago"], minutes=20)
        fin = debut + timedelta(seconds=row["duration_seconds"])

        _, created = upsert_instance(
            Consultation,
            {
                "user": user,
                "document": document,
                "type_consultation": Consultation.TypeConsultation.VUE,
                "debut_consultation": debut,
            },
            {
                "fin_consultation": fin,
                "duree_secondes": row["duration_seconds"],
                "ip_address": "127.0.0.1",
                "user_agent": "seed-script",
            },
        )
        summary["consultations"] += int(created)

        if row["favorite"]:
            _, favorite_created = upsert_instance(
                Favori,
                {"etudiant": etudiant, "document": document},
            )
            summary["favoris"] += int(favorite_created)

    for row in SEARCH_SEEDS:
        user = users_context["users_by_email"][row["email"]]
        debut = reference_time - timedelta(days=row["days_ago"], minutes=5)

        _, created = upsert_instance(
            Consultation,
            {
                "user": user,
                "type_consultation": Consultation.TypeConsultation.RECHERCHE,
                "recherche_query": row["query"],
                "debut_consultation": debut,
            },
            {
                "document": None,
                "fin_consultation": None,
                "duree_secondes": None,
                "ip_address": "127.0.0.1",
                "user_agent": "seed-script",
            },
        )
        summary["recherches"] += int(created)

    print(f"Consultations preparees : {len(CONSULTATION_SEEDS)}")
    print(f"Recherches preparees : {len(SEARCH_SEEDS)}")


def seed_database(*, skip_activity: bool = False) -> dict:
    from django.db import transaction

    summary = {
        "filieres": 0,
        "niveaux": 0,
        "specialites": 0,
        "ues": 0,
        "ecues": 0,
        "users": 0,
        "bibliothecaires": 0,
        "etudiants": 0,
        "documents": 0,
        "consultations": 0,
        "favoris": 0,
        "recherches": 0,
    }

    with transaction.atomic():
        context = seed_catalog(summary)
        users_context = seed_users(context, summary)
        documents_by_title = seed_documents(context, users_context, summary)
        if not skip_activity:
            seed_activity(users_context, documents_by_title, summary)

    print_section("Comptes de connexion")
    print(f"Admin           : admin@ebiblio.local / {ADMIN_PASSWORD}")
    print(f"Bibliothecaire  : biblio.principal@ebiblio.local / {BIBLIOTHECAIRE_PASSWORD}")
    print(f"Etudiant        : etu.info.l1@ebiblio.local / {ETUDIANT_PASSWORD}")

    print_section("Resume")
    for key, value in summary.items():
        print(f"{key}: {value}")

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insere des donnees de demonstration dans la base E-BIBLIO.")
    parser.add_argument(
        "--skip-activity",
        action="store_true",
        help="Insere uniquement le catalogue et les utilisateurs, sans favoris ni consultations.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bootstrap_django()

    try:
        seed_database(skip_activity=args.skip_activity)
    except Exception as exc:
        print("\nEchec du seed.")
        print("Verifiez que la base est accessible et que les migrations ont ete appliquees.")
        print(f"Detail: {exc}")
        return 1

    print("\nSeed termine avec succes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


