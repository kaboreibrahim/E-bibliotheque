"""
Seed 2025 pour E-BIBLIO, aligne sur les modeles Django reels.

Execution :
    python seed_2025.py

Ou depuis un shell Django deja initialise :
    import seed_2025
    seed_2025.seed_all()
"""

from __future__ import annotations

import os
import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal

import django
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone


SEED_YEAR = 2025
NIVEAUX_TRONC_COMMUN = {"L1", "L2", "L3"}
SPECIALITE_DOCTORAT_NAME = "Doctorat en droit"

ADMIN_PASSWORD = "Admin@2025!"
BIBLIO_PASSWORD = "Biblio@2025!"
ETUDIANT_PASSWORD = "Etudiant@2025!"


def bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def get_all_manager(model):
    return getattr(model, "all_objects", model.objects)


def upsert_instance(model, lookup: dict, values: dict | None = None, validate: bool = True):
    values = values or {}
    manager = get_all_manager(model)
    instance = manager.filter(**lookup).order_by("pk").first()
    created = instance is None

    if created:
        instance = model(**lookup)

    for field_name, value in values.items():
        setattr(instance, field_name, value)

    if getattr(instance, "deleted", None):
        instance.deleted = None
        if hasattr(instance, "deleted_by_cascade"):
            instance.deleted_by_cascade = False

    if validate and hasattr(instance, "full_clean"):
        instance.full_clean()

    instance.save()
    return instance, created


def direct_update(instance, **fields):
    if not fields:
        return instance
    get_all_manager(type(instance)).filter(pk=instance.pk).update(**fields)
    for field_name, value in fields.items():
        setattr(instance, field_name, value)
    return instance


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in normalized.lower())
    return " ".join(cleaned.split())


def build_document_path(doc_type: str, title: str) -> str:
    slug = normalize_text(title).replace(" ", "_")[:80]
    return f"documents/{doc_type.lower()}/{slug}.pdf"


def specialite_name_for(filiere_name: str, niveau_name: str) -> str | None:
    if niveau_name in NIVEAUX_TRONC_COMMUN:
        return None
    if niveau_name == "DOCTORAT":
        return SPECIALITE_DOCTORAT_NAME
    return filiere_name


def resolve_seed_email(email: str) -> str:
    return SEED_EMAIL_ALIASES.get(email, email)


def resolve_document(documents, title_fragment: str):
    target = normalize_text(title_fragment)
    target_tokens = {token for token in target.split() if len(token) > 2}
    best_doc = None
    best_score = 0

    for doc in documents:
        normalized_title = normalize_text(doc.title)
        if target in normalized_title or normalized_title in target:
            return doc

        score = len(target_tokens & {token for token in normalized_title.split() if len(token) > 2})
        if score > best_score:
            best_doc = doc
            best_score = score

    return best_doc if best_score >= 2 else None


def build_context():
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau
    from apps.specialites.models import Specialite
    from apps.ue.models import UE, ECUE

    context = {"filieres": {}, "niveaux": {}, "specialites": {}, "ues": {}, "ecues": {}}

    for filiere in Filiere.objects.all():
        context["filieres"][filiere.name] = filiere

    for niveau in Niveau.objects.select_related("filiere").all():
        context["niveaux"][(niveau.filiere.name, niveau.name)] = niveau

    for specialite in Specialite.objects.select_related("niveau", "niveau__filiere").all():
        key = (specialite.niveau.filiere.name, specialite.niveau.name)
        context["specialites"][key] = specialite

    for ue in UE.objects.prefetch_related("niveaux").all():
        context["ues"][ue.code] = ue

    for ecue in ECUE.objects.select_related("ue").all():
        context["ecues"][ecue.ue.code] = ecue

    return context


FILIERE_LEVELS = {
    "Droit (Tronc Commun)": ["L1", "L2", "L3"],
    "Droit des Contentieux": ["M1", "M2"],
    "Droit des Affaires": ["M1", "M2"],
    "Droit Public": ["M1", "M2"],
    "Droit Privé": ["M1", "M2"],
    "Doctorat": ["DOCTORAT"],
}

UE_SEEDS = [
    ("DGL101", "Droit Constitutionnel General", [("Droit (Tronc Commun)", "L1")]),
    ("DGL102", "Droit Civil des Personnes", [("Droit (Tronc Commun)", "L1")]),
    ("DGL103", "Droit Penal General", [("Droit (Tronc Commun)", "L1"), ("Droit (Tronc Commun)", "L2")]),
    ("DGL104", "Introduction au Droit Administratif", [("Droit (Tronc Commun)", "L1")]),
    ("DGL105", "Histoire du Droit", [("Droit (Tronc Commun)", "L2"), ("Droit (Tronc Commun)", "L3")]),
    ("DGL106", "Droit des Obligations", [("Droit (Tronc Commun)", "L2"), ("Droit (Tronc Commun)", "L3")]),
    ("DGL107", "Droit Constitutionnel Ivoirien", [("Droit (Tronc Commun)", "L3")]),
    ("DGL108", "Droit Administratif General", [("Droit (Tronc Commun)", "L3")]),
    ("COC2102", "Contentieux constitutionnel", [("Droit des Contentieux", "M1")]),
    ("COA2101", "Contentieux administratif", [("Droit des Contentieux", "M1")]),
    ("CCI2103", "Contentieux civil", [("Droit des Contentieux", "M1")]),
    ("COF2104", "Contentieux fiscal", [("Droit des Contentieux", "M1")]),
    ("CPN2105", "Contentieux penal", [("Droit des Contentieux", "M1")]),
    ("CIP2201", "Contentieux international public", [("Droit des Contentieux", "M2")]),
    ("CIE2202", "Contentieux international economique", [("Droit des Contentieux", "M2")]),
    ("CCM2203", "Contentieux commercial", [("Droit des Contentieux", "M2")]),
    ("VEX2204", "Voies d'execution et procedure d'urgence", [("Droit des Contentieux", "M2")]),
    ("DPR2206", "Droit de la preuve", [("Droit des Contentieux", "M2")]),
    ("CPB2301", "Contentieux interne public specialise", [("Droit des Contentieux", "M2")]),
    ("CIS2302", "Contentieux international specialise", [("Droit des Contentieux", "M2")]),
    ("DER2303", "Droit de l'arbitrage", [("Droit des Contentieux", "M2")]),
    ("DIC2304", "Contentieux international penal", [("Droit des Contentieux", "M2")]),
    ("RAC2305", "Redaction d'actes", [("Droit des Contentieux", "M2")]),
    ("TCC2307", "Memoire", [("Droit des Contentieux", "M2")]),
    ("DAC3101", "Droit des Societes", [("Droit des Affaires", "M1")]),
    ("DAC3102", "Droit Commercial General", [("Droit des Affaires", "M1")]),
    ("DAC3103", "Droit Bancaire et Financier", [("Droit des Affaires", "M1")]),
    ("DAC3104", "Droit Fiscal des Entreprises", [("Droit des Affaires", "M1")]),
    ("DAC3105", "Droit de la Concurrence", [("Droit des Affaires", "M1")]),
    ("DAC3201", "Droit International des Affaires", [("Droit des Affaires", "M2")]),
    ("DAC3202", "Droit Boursier et Marches Financiers", [("Droit des Affaires", "M2")]),
    ("DAC3203", "Propriete Intellectuelle", [("Droit des Affaires", "M2")]),
    ("DAC3204", "Droit des Nouvelles Technologies", [("Droit des Affaires", "M2")]),
    ("TDA3205", "Memoire Droit des Affaires", [("Droit des Affaires", "M2")]),
    ("DPB4101", "Droit Administratif Approfondi", [("Droit Public", "M1")]),
    ("DPB4102", "Droit Constitutionnel Compare", [("Droit Public", "M1")]),
    ("DPB4103", "Droit des Libertes Fondamentales", [("Droit Public", "M1")]),
    ("DPB4104", "Droit Public Economique", [("Droit Public", "M1")]),
    ("DPB4105", "Droit de l'Urbanisme", [("Droit Public", "M1")]),
    ("DPB4201", "Droit International Public", [("Droit Public", "M2")]),
    ("DPB4202", "Droit Communautaire", [("Droit Public", "M2")]),
    ("DPB4203", "Droit de l'Environnement", [("Droit Public", "M2")]),
    ("DPB4204", "Droit Fiscal Public", [("Droit Public", "M2")]),
    ("TDP4205", "Memoire Droit Public", [("Droit Public", "M2")]),
    ("DPR5101", "Droit Civil Approfondi", [("Droit Privé", "M1")]),
    ("DPR5102", "Droit des Contrats Speciaux", [("Droit Privé", "M1")]),
    ("DPR5103", "Droit des Suretes", [("Droit Privé", "M1")]),
    ("DPR5104", "Droit de la Famille", [("Droit Privé", "M1")]),
    ("DPR5105", "Droit des Successions", [("Droit Privé", "M1")]),
    ("DPR5201", "Droit International Prive", [("Droit Privé", "M2")]),
    ("DPR5202", "Droit des Responsabilites", [("Droit Privé", "M2")]),
    ("DPR5203", "Droit Immobilier", [("Droit Privé", "M2")]),
    ("DPR5204", "Droit Penal des Affaires", [("Droit Privé", "M2")]),
    ("TDR5205", "Memoire Droit Privé", [("Droit Privé", "M2")]),
]

ADMIN_SEED = {
    "email": "admin@universite-ci.edu",
    "first_name": "Kouame",
    "last_name": "BROU",
    "phone": "+2250701000001",
}

BIBLIOTHECAIRES = [
    {
        "email": "biblio.kone@universite-ci.edu",
        "first_name": "Mariam",
        "last_name": "KONE",
        "phone": "+2250701000002",
        "badge": "BIB-2025-001",
    },
    {
        "email": "biblio.diallo@universite-ci.edu",
        "first_name": "Seydou",
        "last_name": "DIALLO",
        "phone": "+2250701000003",
        "badge": "BIB-2025-002",
    },
]

ETUDIANTS_LICENCE = {
    "L1": [
        {"email": "etu.l1.kone@etud-ci.edu", "first_name": "Yao", "last_name": "KONE", "phone": "+2250701003001"},
        {"email": "etu.l1.brou@etud-ci.edu", "first_name": "Aminata", "last_name": "BROU", "phone": "+2250701003002"},
        {"email": "etu.l1.toure@etud-ci.edu", "first_name": "Moussa", "last_name": "TOURE", "phone": "+2250701003003"},
    ],
    "L2": [
        {"email": "etu.l2.sangare@etud-ci.edu", "first_name": "Fatou", "last_name": "SANGARE", "phone": "+2250701004001"},
        {"email": "etu.l2.ouedraogo@etud-ci.edu", "first_name": "Kouakou", "last_name": "OUEDRAOGO", "phone": "+2250701004002"},
        {"email": "etu.l2.kone@etud-ci.edu", "first_name": "Adama", "last_name": "KONE", "phone": "+2250701004003"},
    ],
    "L3": [
        {"email": "etu.l3.coulibaly@etud-ci.edu", "first_name": "Brahima", "last_name": "COULIBALY", "phone": "+2250701005001"},
        {"email": "etu.l3.diarra@etud-ci.edu", "first_name": "Mariam", "last_name": "DIARRA", "phone": "+2250701005002"},
        {"email": "etu.l3.bamba@etud-ci.edu", "first_name": "Seydou", "last_name": "BAMBA", "phone": "+2250701005003"},
    ],
}

ETUDIANTS_SPECIALISES = {
    ("Droit des Contentieux", "M1"): [
        {"email": "etu.dc.m1.kouassi@etud-ci.edu", "first_name": "Adjoua", "last_name": "KOUASSI", "phone": "+2250701001001"},
        {"email": "etu.dc.m1.traore@etud-ci.edu", "first_name": "Ibrahim", "last_name": "TRAORE", "phone": "+2250701001002"},
    ],
    ("Droit des Contentieux", "M2"): [
        {"email": "etu.dc.m2.ouattara@etud-ci.edu", "first_name": "Salimata", "last_name": "OUATTARA", "phone": "+2250701002001"},
        {"email": "etu.dc.m2.koffi@etud-ci.edu", "first_name": "Jean-Marc", "last_name": "KOFFI", "phone": "+2250701002002"},
    ],
    ("Droit des Affaires", "M1"): [
        {"email": "etu.da.m1.yao@etud-ci.edu", "first_name": "Brice", "last_name": "YAO", "phone": "+2250701006001"},
        {"email": "etu.da.m1.coulibaly@etud-ci.edu", "first_name": "Fatou", "last_name": "COULIBALY", "phone": "+2250701006002"},
    ],
    ("Droit des Affaires", "M2"): [
        {"email": "etu.da.m2.gbagbo@etud-ci.edu", "first_name": "Olivia", "last_name": "GBAGBO", "phone": "+2250701007001"},
        {"email": "etu.da.m2.n_goran@etud-ci.edu", "first_name": "Rachel", "last_name": "N'GORAN", "phone": "+2250701007002"},
    ],
    ("Droit Public", "M1"): [
        {"email": "etu.dp.m1.kone@etud-ci.edu", "first_name": "Kouame", "last_name": "KONE", "phone": "+2250701008001"},
        {"email": "etu.dp.m1.bamba@etud-ci.edu", "first_name": "Moussa", "last_name": "BAMBA", "phone": "+2250701008002"},
    ],
    ("Droit Public", "M2"): [
        {"email": "etu.dp.m2.ahui@etud-ci.edu", "first_name": "Prisca", "last_name": "AHUI", "phone": "+2250701009001"},
        {"email": "etu.dp.m2.diallo@etud-ci.edu", "first_name": "Seydou", "last_name": "DIALLO", "phone": "+2250701009002"},
    ],
    ("Droit Privé", "M1"): [
        {"email": "etu.dpr.m1.toure@etud-ci.edu", "first_name": "Aminata", "last_name": "TOURE", "phone": "+2250701010001"},
        {"email": "etu.dpr.m1.sangare@etud-ci.edu", "first_name": "Brahima", "last_name": "SANGARE", "phone": "+2250701010002"},
    ],
    ("Droit Privé", "M2"): [
        {"email": "etu.dpr.m2.ouedraogo@etud-ci.edu", "first_name": "Kouakou", "last_name": "OUEDRAOGO", "phone": "+2250701011001"},
        {"email": "etu.dpr.m2.diarra@etud-ci.edu", "first_name": "Mariam", "last_name": "DIARRA", "phone": "+2250701011002"},
    ],
    ("Doctorat", "DOCTORAT"): [
        {"email": "doc.these1@doctorant-ci.edu", "first_name": "Jean", "last_name": "KOUADJA", "phone": "+2250702000001"},
        {"email": "doc.these2@doctorant-ci.edu", "first_name": "Marie", "last_name": "TOURE", "phone": "+2250702000002"},
        {"email": "doc.these3@doctorant-ci.edu", "first_name": "Paul", "last_name": "SANGARE", "phone": "+2250702000003"},
    ],
}

DOCUMENT_SEEDS = [
    {"title": "Cours - Introduction au droit constitutionnel", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L1", "ue_code": "DGL101", "encadreur": "Pr. KONAN Yapo", "days_ago": 120},
    {"title": "Cours - Droit civil des personnes physiques", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L1", "ue_code": "DGL102", "encadreur": "Dr. TOURE Awa", "days_ago": 115},
    {"title": "Examen L1 - Droit constitutionnel general", "type": "EXAMEN", "filiere": "Droit (Tronc Commun)", "niveau": "L1", "ue_code": "DGL101", "encadreur": "Pr. KONAN Yapo", "days_ago": 90},
    {"title": "Cours - Droit des obligations", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L2", "ue_code": "DGL106", "encadreur": "Pr. BAMBA Kouame", "days_ago": 110},
    {"title": "Cours - Droit penal general", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L2", "ue_code": "DGL103", "encadreur": "Dr. SANGARE Adama", "days_ago": 105},
    {"title": "Examen L2 - Droit des obligations", "type": "EXAMEN", "filiere": "Droit (Tronc Commun)", "niveau": "L2", "ue_code": "DGL106", "encadreur": "Pr. BAMBA Kouame", "days_ago": 80},
    {"title": "Cours - Droit administratif general", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L3", "ue_code": "DGL108", "encadreur": "Pr. OUATTARA Bakary", "days_ago": 100},
    {"title": "Cours - Histoire du droit", "type": "COURS", "filiere": "Droit (Tronc Commun)", "niveau": "L3", "ue_code": "DGL105", "encadreur": "Dr. KONATE Fatou", "days_ago": 95},
    {"title": "Examen L3 - Droit administratif", "type": "EXAMEN", "filiere": "Droit (Tronc Commun)", "niveau": "L3", "ue_code": "DGL108", "encadreur": "Pr. OUATTARA Bakary", "days_ago": 70},
    {"title": "Cours - Le controle par voie d'action", "type": "COURS", "filiere": "Droit des Contentieux", "niveau": "M1", "ue_code": "COC2102", "encadreur": "Pr. ASSI Jean-Baptiste", "days_ago": 90},
    {"title": "Cours - La responsabilite administrative", "type": "COURS", "filiere": "Droit des Contentieux", "niveau": "M1", "ue_code": "COA2101", "encadreur": "Dr. KONAN Adjoua Marie", "days_ago": 85},
    {"title": "Examen M1 - Contentieux constitutionnel", "type": "EXAMEN", "filiere": "Droit des Contentieux", "niveau": "M1", "ue_code": "COC2102", "encadreur": "Pr. ASSI Jean-Baptiste", "days_ago": 60},
    {"title": "Cours - Contentieux electoral", "type": "COURS", "filiere": "Droit des Contentieux", "niveau": "M2", "ue_code": "CPB2301", "encadreur": "Pr. ASSI Jean-Baptiste", "days_ago": 45},
    {"title": "Cours - Arbitrage regional et national", "type": "COURS", "filiere": "Droit des Contentieux", "niveau": "M2", "ue_code": "DER2303", "encadreur": "Pr. KOFFI Edmond", "days_ago": 40},
    {"title": "Memoire - L'arbitrage OHADA face aux juridictions etatiques", "type": "MEMOIRE", "filiere": "Droit des Contentieux", "niveau": "M2", "ue_code": "TCC2307", "auteur": "OUATTARA Salimata", "encadreur": "Pr. KOFFI Edmond", "days_ago": 30},
    {"title": "Memoire - Le recours en annulation devant le Conseil d'Etat", "type": "MEMOIRE", "filiere": "Droit des Contentieux", "niveau": "M2", "ue_code": "TCC2307", "auteur": "KOFFI Jean-Marc", "encadreur": "Dr. KONAN Adjoua Marie", "days_ago": 25},
    {"title": "Cours - Droit des societes commerciales", "type": "COURS", "filiere": "Droit des Affaires", "niveau": "M1", "ue_code": "DAC3101", "encadreur": "Pr. YAO Kouame", "days_ago": 88},
    {"title": "Cours - Droit bancaire et financier", "type": "COURS", "filiere": "Droit des Affaires", "niveau": "M1", "ue_code": "DAC3103", "encadreur": "Dr. KONE Mariam", "days_ago": 83},
    {"title": "Examen M1 - Droit des societes", "type": "EXAMEN", "filiere": "Droit des Affaires", "niveau": "M1", "ue_code": "DAC3101", "encadreur": "Pr. YAO Kouame", "days_ago": 58},
    {"title": "Cours - Propriete intellectuelle", "type": "COURS", "filiere": "Droit des Affaires", "niveau": "M2", "ue_code": "DAC3203", "encadreur": "Pr. DIALLO Seydou", "days_ago": 43},
    {"title": "Memoire - La protection des marques en Afrique", "type": "MEMOIRE", "filiere": "Droit des Affaires", "niveau": "M2", "ue_code": "TDA3205", "auteur": "GBAGBO Olivia", "encadreur": "Pr. DIALLO Seydou", "days_ago": 28},
    {"title": "Cours - Droit administratif approfondi", "type": "COURS", "filiere": "Droit Public", "niveau": "M1", "ue_code": "DPB4101", "encadreur": "Pr. TOURE Issiaka", "days_ago": 86},
    {"title": "Cours - Droit des libertes fondamentales", "type": "COURS", "filiere": "Droit Public", "niveau": "M1", "ue_code": "DPB4103", "encadreur": "Dr. BONI Clarisse", "days_ago": 81},
    {"title": "Examen M1 - Droit administratif", "type": "EXAMEN", "filiere": "Droit Public", "niveau": "M1", "ue_code": "DPB4101", "encadreur": "Pr. TOURE Issiaka", "days_ago": 56},
    {"title": "Cours - Droit international public", "type": "COURS", "filiere": "Droit Public", "niveau": "M2", "ue_code": "DPB4201", "encadreur": "Pr. KOFFI Edmond", "days_ago": 41},
    {"title": "Memoire - Le contentieux electoral en Afrique de l'Ouest", "type": "MEMOIRE", "filiere": "Droit Public", "niveau": "M2", "ue_code": "TDP4205", "auteur": "AHUI Prisca", "encadreur": "Pr. TOURE Issiaka", "days_ago": 26},
    {"title": "Cours - Droit civil approfondi", "type": "COURS", "filiere": "Droit Privé", "niveau": "M1", "ue_code": "DPR5101", "encadreur": "Pr. COULIBALY Nathalie", "days_ago": 84},
    {"title": "Cours - Droit des suretes", "type": "COURS", "filiere": "Droit Privé", "niveau": "M1", "ue_code": "DPR5103", "encadreur": "Dr. GNANGUI Pamela", "days_ago": 79},
    {"title": "Examen M1 - Droit civil", "type": "EXAMEN", "filiere": "Droit Privé", "niveau": "M1", "ue_code": "DPR5101", "encadreur": "Pr. COULIBALY Nathalie", "days_ago": 54},
    {"title": "Cours - Droit international prive", "type": "COURS", "filiere": "Droit Privé", "niveau": "M2", "ue_code": "DPR5201", "encadreur": "Pr. CAMARA Bintou", "days_ago": 39},
    {"title": "Memoire - La preuve electronique dans le contentieux civil", "type": "MEMOIRE", "filiere": "Droit Privé", "niveau": "M2", "ue_code": "TDR5205", "auteur": "N'GORAN Rachel", "encadreur": "Dr. GNANGUI Pamela", "days_ago": 24},
    {"title": "These - L'effectivite des decisions de la Cour CEDEAO des droits de l'homme", "type": "THESE", "filiere": "Doctorat", "niveau": "DOCTORAT", "auteur": "KOUADJA Jean", "encadreur": "Pr. ASSI Jean-Baptiste", "days_ago": 20},
    {"title": "These - Le contentieux electoral en Afrique de l'Ouest : etude comparee", "type": "THESE", "filiere": "Doctorat", "niveau": "DOCTORAT", "auteur": "TOURE Marie", "encadreur": "Pr. TOURE Issiaka", "days_ago": 18},
    {"title": "These - L'arbitrage international en matiere d'investissement", "type": "THESE", "filiere": "Doctorat", "niveau": "DOCTORAT", "auteur": "SANGARE Paul", "encadreur": "Pr. KOFFI Edmond", "days_ago": 15},
]

INTERACTION_SEEDS = [
    ("etu.dc.m1.kouassi@etud-ci.edu", [
        ("Cours - Le controle par voie d'action", 420, True),
        ("Cours - La responsabilite administrative", 360, True),
        ("Examen M1 - Contentieux constitutionnel", 180, True),
        ("Memoire - L'arbitrage OHADA face aux juridictions etatiques", 600, False),
    ]),
    ("etu.dc.m1.traore@etud-ci.edu", [
        ("Cours - Droit civil approfondi", 500, True),
        ("Cours - Droit penal general", 310, False),
        ("Examen M1 - Droit administratif", 240, True),
        ("These - Le contentieux electoral en Afrique de l'Ouest : etude comparee", 720, True),
    ]),
    ("etu.da.m1.yao@etud-ci.edu", [
        ("Cours - Droit des suretes", 280, False),
        ("Cours - Arbitrage regional et national", 450, True),
        ("Cours - Arbitrage regional et national", 200, True),
        ("Memoire - Le recours en annulation devant le Conseil d'Etat", 530, False),
    ]),
    ("etu.dpr.m1.toure@etud-ci.edu", [
        ("Cours - Droit international public", 390, True),
        ("Cours - Droit civil des personnes physiques", 260, True),
        ("These - L'effectivite des decisions de la Cour CEDEAO des droits de l'homme", 810, True),
        ("Memoire - La preuve electronique dans le contentieux civil", 430, True),
    ]),
    ("etu.da.m2.gbagbo@etud-ci.edu", [
        ("Cours - Propriete intellectuelle", 340, False),
        ("Cours - Droit des societes commerciales", 290, True),
        ("Memoire - La protection des marques en Afrique", 480, True),
        ("Cours - Droit international public", 150, False),
    ]),
    ("etu.dc.m2.ouattara@etud-ci.edu", [
        ("Cours - Contentieux electoral", 520, True),
        ("Cours - Arbitrage regional et national", 410, True),
        ("Memoire - L'arbitrage OHADA face aux juridictions etatiques", 900, True),
        ("These - Le contentieux electoral en Afrique de l'Ouest : etude comparee", 660, True),
    ]),
    ("etu.dc.m2.koffi@etud-ci.edu", [
        ("Cours - Droit international public", 430, True),
        ("Memoire - Le recours en annulation devant le Conseil d'Etat", 580, False),
        ("These - L'effectivite des decisions de la Cour CEDEAO des droits de l'homme", 750, False),
        ("Cours - Droit administratif approfondi", 260, True),
    ]),
    ("etu.da.m2.n_goran@etud-ci.edu", [
        ("Cours - Droit civil des personnes physiques", 300, True),
        ("Memoire - La preuve electronique dans le contentieux civil", 680, True),
        ("Cours - Arbitrage regional et national", 490, False),
        ("Cours - Propriete intellectuelle", 220, True),
    ]),
    ("etu.dp.m2.ahui@etud-ci.edu", [
        ("These - Le contentieux electoral en Afrique de l'Ouest : etude comparee", 840, True),
        ("Cours - Contentieux electoral", 360, True),
        ("Examen M1 - Contentieux constitutionnel", 190, False),
        ("Cours - Le controle par voie d'action", 440, False),
    ]),
    ("etu.dp.m2.diallo@etud-ci.edu", [
        ("These - L'effectivite des decisions de la Cour CEDEAO des droits de l'homme", 920, True),
        ("Cours - Droit des suretes", 260, False),
        ("Memoire - L'arbitrage OHADA face aux juridictions etatiques", 510, True),
        ("Examen M1 - Droit administratif", 280, True),
    ]),
]

SEARCH_SEEDS = [
    ("etu.dc.m1.kouassi@etud-ci.edu", "arbitrage OHADA", -20),
    ("etu.dc.m1.traore@etud-ci.edu", "contentieux civil", -18),
    ("etu.da.m1.yao@etud-ci.edu", "procedures d'urgence", -15),
    ("etu.dpr.m1.toure@etud-ci.edu", "preuve electronique", -12),
    ("etu.da.m2.gbagbo@etud-ci.edu", "contentieux international", -10),
    ("etu.dc.m2.ouattara@etud-ci.edu", "memoire arbitrage", -8),
    ("etu.dc.m2.koffi@etud-ci.edu", "examen droit penal", -6),
    ("etu.da.m2.n_goran@etud-ci.edu", "redaction actes juridiques", -5),
    ("etu.dp.m2.ahui@etud-ci.edu", "contentieux electoral", -4),
    ("etu.dp.m2.diallo@etud-ci.edu", "CEDEAO droits homme", -3),
]

SEED_EMAIL_ALIASES = {
    "etu.kouassi@etud-ci.edu": "etu.dc.m1.kouassi@etud-ci.edu",
    "etu.traore@etud-ci.edu": "etu.dc.m1.traore@etud-ci.edu",
    "etu.yao@etud-ci.edu": "etu.da.m1.yao@etud-ci.edu",
    "etu.coulibaly@etud-ci.edu": "etu.da.m1.coulibaly@etud-ci.edu",
    "etu.gbagbo@etud-ci.edu": "etu.da.m2.gbagbo@etud-ci.edu",
    "etu.ouattara@etud-ci.edu": "etu.dc.m2.ouattara@etud-ci.edu",
    "etu.koffi@etud-ci.edu": "etu.dc.m2.koffi@etud-ci.edu",
    "etu.n_goran@etud-ci.edu": "etu.da.m2.n_goran@etud-ci.edu",
    "etu.bamba@etud-ci.edu": "etu.dp.m1.bamba@etud-ci.edu",
    "etu.ahui@etud-ci.edu": "etu.dp.m2.ahui@etud-ci.edu",
}


def seed_all(seed_history: bool = True):
    context = seed_filieres_niveaux()
    context = seed_ues_ecues(context)
    seed_utilisateurs(context)
    seed_documents(context)
    seed_consultations_favoris(seed_history=seed_history)
    print("\nSEED 2025 termine avec succes.\n")


@transaction.atomic
def seed_filieres_niveaux():
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau
    from apps.specialites.models import Specialite

    print("Creation filieres, niveaux et specialites...")

    created_filieres = 0
    created_niveaux = 0
    created_specialites = 0
    context = {"filieres": {}, "niveaux": {}, "specialites": {}, "ues": {}, "ecues": {}}

    for filiere_name, level_names in FILIERE_LEVELS.items():
        filiere, filiere_created = upsert_instance(Filiere, {"name": filiere_name})
        created_filieres += int(filiere_created)
        context["filieres"][filiere_name] = filiere

        for level_name in level_names:
            niveau, niveau_created = upsert_instance(Niveau, {"filiere": filiere, "name": level_name})
            created_niveaux += int(niveau_created)
            context["niveaux"][(filiere_name, level_name)] = niveau

            specialite_name = specialite_name_for(filiere_name, level_name)
            if not specialite_name:
                continue

            specialite, specialite_created = upsert_instance(
                Specialite,
                {"name": specialite_name, "niveau": niveau},
            )
            created_specialites += int(specialite_created)
            context["specialites"][(filiere_name, level_name)] = specialite

    print(f"  Filieres pretes : {len(context['filieres'])} ({created_filieres} nouvelles)")
    print(f"  Niveaux prets : {len(context['niveaux'])} ({created_niveaux} nouveaux)")
    print(f"  Specialites pretes : {len(context['specialites'])} ({created_specialites} nouvelles)")
    return context


@transaction.atomic
def seed_ues_ecues(context=None):
    from apps.ue.models import UE, ECUE

    context = context or build_context()
    context.setdefault("ues", {})
    context.setdefault("ecues", {})
    print("\nCreation UEs et ECUEs...")

    created_ues = 0
    created_ecues = 0

    for code, name, level_refs in UE_SEEDS:
        ue, ue_created = upsert_instance(
            UE,
            {"code": code},
            {"name": name, "coef": Decimal("0.00")},
        )
        created_ues += int(ue_created)
        ue.niveaux.set([context["niveaux"][ref] for ref in level_refs])

        ecue, ecue_created = upsert_instance(
            ECUE,
            {"ue": ue, "code": f"{code}01"},
            {"name": f"{name} - Cours", "coef": Decimal("5.00")},
        )
        created_ecues += int(ecue_created)

        ue.sync_coef_from_ecues()
        context["ues"][code] = ue
        context["ecues"][code] = ecue

    print(f"  UEs pretes : {len(context['ues'])} ({created_ues} nouvelles)")
    print(f"  ECUEs pretes : {len(context['ecues'])} ({created_ecues} nouvelles)")
    return context


def upsert_user(email: str, raw_password: str, **values):
    from apps.users.models import User

    defaults = dict(values)
    defaults["password"] = make_password(raw_password)
    return upsert_instance(User, {"email": email}, defaults)


@transaction.atomic
def seed_utilisateurs(context=None):
    from apps.users.models import User
    from apps.users.models.bibliothecaire_models import Bibliothecaire
    from apps.users.models.etudiant_models import Etudiant

    context = context or build_context()
    print("\nCreation des utilisateurs...")

    activation_base = timezone.now() - timedelta(days=10)

    admin, _ = upsert_user(
        ADMIN_SEED["email"],
        ADMIN_PASSWORD,
        first_name=ADMIN_SEED["first_name"],
        last_name=ADMIN_SEED["last_name"],
        phone=ADMIN_SEED["phone"],
        user_type=User.UserType.ADMINISTRATEUR,
        is_staff=True,
        is_superuser=True,
        is_active=True,
        is_2fa_enabled=True,
    )

    for data in BIBLIOTHECAIRES:
        user, _ = upsert_user(
            data["email"],
            BIBLIO_PASSWORD,
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            user_type=User.UserType.BIBLIOTHECAIRE,
            is_staff=True,
            is_superuser=False,
            is_active=True,
            is_2fa_enabled=True,
        )
        upsert_instance(
            Bibliothecaire,
            {"user": user},
            {
                "badge_number": data["badge"],
                "date_prise_poste": datetime(SEED_YEAR, 1, 6).date(),
                "peut_gerer_documents": True,
                "peut_gerer_utilisateurs": True,
            },
        )

    total_etudiants = 0

    for niveau_name, student_rows in ETUDIANTS_LICENCE.items():
        filiere_name = "Droit (Tronc Commun)"
        filiere = context["filieres"][filiere_name]
        niveau = context["niveaux"][(filiere_name, niveau_name)]

        for data in student_rows:
            user, _ = upsert_user(
                data["email"],
                ETUDIANT_PASSWORD,
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.ETUDIANT,
                is_staff=False,
                is_superuser=False,
                is_active=True,
                is_2fa_enabled=False,
            )
            etudiant, _ = upsert_instance(
                Etudiant,
                {"user": user},
                {
                    "filiere": filiere,
                    "niveau": niveau,
                    "specialite": None,
                    "annee_inscription": SEED_YEAR,
                    "compte_active_le": activation_base,
                    "nb_reactivations": 0,
                    "derniere_reactivation_par": None,
                },
            )
            total_etudiants += 1
            print(f"  Etudiant {niveau_name} : {user.email} -> {etudiant.matricule}")

    for (filiere_name, niveau_name), student_rows in ETUDIANTS_SPECIALISES.items():
        filiere = context["filieres"][filiere_name]
        niveau = context["niveaux"][(filiere_name, niveau_name)]
        specialite = context["specialites"].get((filiere_name, niveau_name))

        for data in student_rows:
            user, _ = upsert_user(
                data["email"],
                ETUDIANT_PASSWORD,
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone=data["phone"],
                user_type=User.UserType.ETUDIANT,
                is_staff=False,
                is_superuser=False,
                is_active=True,
                is_2fa_enabled=False,
            )
            etudiant, _ = upsert_instance(
                Etudiant,
                {"user": user},
                {
                    "filiere": filiere,
                    "niveau": niveau,
                    "specialite": specialite,
                    "annee_inscription": SEED_YEAR,
                    "compte_active_le": activation_base,
                    "nb_reactivations": 0,
                    "derniere_reactivation_par": admin,
                },
            )
            total_etudiants += 1
            print(f"  Etudiant {niveau_name} {filiere_name} : {user.email} -> {etudiant.matricule}")

    print(f"  Admin pret : {admin.email}")
    print(f"  Bibliothecaires prets : {len(BIBLIOTHECAIRES)}")
    print(f"  Etudiants prets : {total_etudiants}")


@transaction.atomic
def seed_documents(context=None):
    from apps.documents.models import Document
    from apps.users.models import User

    context = context or build_context()
    print("\nCreation des documents...")

    biblio = User.objects.get(email="biblio.kone@universite-ci.edu")
    created_count = 0
    reference_date = timezone.make_aware(datetime(SEED_YEAR, 12, 31, 10, 0, 0))

    for row in DOCUMENT_SEEDS:
        filiere_name = row["filiere"]
        niveau_name = row["niveau"]
        filiere = context["filieres"][filiere_name]
        niveau = context["niveaux"][(filiere_name, niveau_name)]
        specialite = context["specialites"].get((filiere_name, niveau_name))
        ecue = context["ecues"].get(row.get("ue_code")) if row.get("ue_code") else None
        timestamp = reference_date - timedelta(days=row["days_ago"])

        document, created = upsert_instance(
            Document,
            {"title": row["title"]},
            {
                "type": row["type"],
                "filiere": filiere,
                "niveau": niveau,
                "specialite": specialite,
                "ue": ecue,
                "auteur": row.get("auteur", ""),
                "encadreur": row.get("encadreur", ""),
                "file_path": build_document_path(row["type"], row["title"]),
                "description": f"Seed {SEED_YEAR} - {row['type']} - {filiere_name} - {niveau_name}",
                "ajoute_par": biblio,
            },
        )
        direct_update(document, created_at=timestamp, updated_at=timestamp)
        created_count += int(created)

    print(f"  Documents prets : {len(DOCUMENT_SEEDS)} ({created_count} nouveaux)")


@transaction.atomic
def seed_consultations_favoris(seed_history: bool = True):
    from apps.consultations.models import Consultation
    from apps.documents.models import Document
    from apps.favoris.models import Favori
    from apps.users.models import User
    from apps.users.models.etudiant_models import Etudiant

    print("\nCreation des consultations et favoris...")

    documents = list(Document.objects.all())
    if not documents:
        print("  Aucun document trouve, section ignoree.")
        return

    base_consultation = timezone.make_aware(datetime(SEED_YEAR, 11, 20, 9, 0, 0))
    created_consultations = 0
    created_favoris = 0
    created_searches = 0
    missing_users = set()
    missing_docs = []

    for email, actions in INTERACTION_SEEDS:
        resolved_email = resolve_seed_email(email)
        user = User.objects.filter(email=resolved_email).first()
        etudiant = Etudiant.objects.filter(user=user).first() if user else None

        if not user or not etudiant:
            missing_users.add(email)
            continue

        for index, (title_fragment, duration_seconds, add_to_favorites) in enumerate(actions):
            document = resolve_document(documents, title_fragment)
            if not document:
                missing_docs.append((email, title_fragment))
                continue

            start_at = base_consultation - timedelta(days=14 - index, hours=index * 2)
            end_at = start_at + timedelta(seconds=duration_seconds)

            consultation, created = upsert_instance(
                Consultation,
                {
                    "user": user,
                    "document": document,
                    "type_consultation": Consultation.TypeConsultation.VUE,
                    "debut_consultation": start_at,
                },
                {
                    "fin_consultation": end_at,
                    "duree_secondes": duration_seconds,
                    "ip_address": f"192.168.1.{10 + index}",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
                },
            )
            direct_update(consultation, created_at=end_at)
            created_consultations += int(created)

            if add_to_favorites:
                _, favori_created = upsert_instance(Favori, {"etudiant": etudiant, "document": document})
                created_favoris += int(favori_created)

    for email, query, offset_days in SEARCH_SEEDS:
        resolved_email = resolve_seed_email(email)
        user = User.objects.filter(email=resolved_email).first()
        if not user:
            missing_users.add(email)
            continue

        start_at = base_consultation + timedelta(days=offset_days)
        search, created = upsert_instance(
            Consultation,
            {
                "user": user,
                "type_consultation": Consultation.TypeConsultation.RECHERCHE,
                "recherche_query": query,
            },
            {
                "document": None,
                "debut_consultation": start_at,
                "fin_consultation": None,
                "duree_secondes": None,
                "ip_address": "192.168.1.50",
                "user_agent": "Mozilla/5.0 (Android 14) Mobile",
            },
        )
        direct_update(search, created_at=start_at)
        created_searches += int(created)

    print(f"  Consultations pretes : {created_consultations} nouvelles")
    print(f"  Favoris prets : {created_favoris} nouveaux")
    print(f"  Recherches pretes : {created_searches} nouvelles")

    if missing_users:
        print(f"  Utilisateurs introuvables : {len(missing_users)}")
    if missing_docs:
        print(f"  Documents introuvables : {len(missing_docs)}")

    if seed_history:
        admin_user = User.objects.filter(email="admin@universite-ci.edu").first()
        biblio_user = User.objects.filter(email="biblio.kone@universite-ci.edu").first()
        if admin_user and biblio_user:
            seed_historique_actions(admin_user, biblio_user)


def seed_historique_actions(admin_user, biblio_user):
    try:
        from apps.documents.models import Document
        from apps.history.models import HistoriqueActionService as HAS
        from apps.users.models import User
        from django.conf import settings
    except Exception as exc:
        print(f"  Historique ignore : {exc}")
        return

    if not hasattr(settings, "MONGODB"):
        print("  Historique ignore : configuration settings.MONGODB absente.")
        return

    print("\nInsertion des logs MongoDB...")

    users = list(User.objects.filter(user_type=User.UserType.ETUDIANT)[:8])
    documents = list(Document.objects.all()[:5])
    logs_attempted = 0

    for index, user in enumerate(users):
        HAS.log_connexion(user=user, statut="succes", ip=f"192.168.1.{20 + index}", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    for user in users[:3]:
        HAS.log_connexion(user=user, statut="echec", ip="10.0.0.99", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    for user in users[:2]:
        HAS.log(
            action=HAS.ACTIONS.OTP_ECHEC,
            user=user,
            statut="echec",
            ip_address="10.0.0.50",
            user_agent="Mozilla/5.0 Safari/605.1.15",
            details={"type_otp": "email", "tentatives": 2},
        )
        logs_attempted += 1

    for staff_user in [admin_user, biblio_user]:
        HAS.log_totp(user=staff_user, statut="succes", ip="192.168.0.10", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    for document in documents:
        HAS.log_document("AJOUT", user=biblio_user, document=document, ip="192.168.0.1", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    if documents:
        HAS.log_document(
            "MODIFICATION",
            user=admin_user,
            document=documents[0],
            ip="192.168.0.2",
            ua="Mozilla/5.0 Chrome/120.0",
            details={"champ_modifie": "description", "ancienne_valeur": "v1", "nouvelle_valeur": "v2"},
        )
        logs_attempted += 1

    for user in users[:3]:
        HAS.log_utilisateur("CREATION", auteur=admin_user, cible_user=user, ip="192.168.0.3", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    for user in users[:5]:
        HAS.log_deconnexion(user=user, ip="192.168.1.30", ua="Mozilla/5.0 Chrome/120.0")
        logs_attempted += 1

    print(f"  Logs Mongo demandes : {logs_attempted}")


if __name__ == "__main__":
    bootstrap_django()
    seed_all()
