"""
Seed du catalogue pedagogique (UE/ECUE) des Master 1 et Master 2 de la
filiere "Sciences juridiques, administratives et politiques", a partir de
la maquette UFR 2024-2025. Complete seed_maquette_droit_l1_l3.py (L1, L2, L3).

Perimetre : M1 et M2, parcours "Droit public fondamental", "Droit prive
fondamental", "Histoire du droit et des institutions", "Science politique".
Ces 4 specialites existent deja en base pour M1 et M2 (voir Specialite) et
sont reutilisees par leur nom exact (get_or_create), pas recreees.

Codes UE partages entre parcours (verifies un par un dans la maquette
source) :
  - M1 : CSP3141 ("Contrats spéciaux"), FPA3141 ("Droit de la fonction
    publique et science administrative"), VEX3142 ("Voies d'exécution")
    apparaissent avec le meme nom et le meme total CEC dans 2 parcours —
    traites comme une seule UE partagee (ManyToMany vers les 2 specialites).
  - M2 : TGD3153 ("Théorie générale du droit"), MER3153 ("Méthodologie de
    la recherche"), ARO3153 ("Art oratoire"), MEM3154 ("Mémoire")
    apparaissent identiquement dans les parcours Droit public fondamental,
    Droit prive fondamental et Histoire du droit et des institutions —
    traites comme des UE partagees (ManyToMany vers les 3 specialites).

Codes UE en collision avec un contenu different (renommes pour respecter la
contrainte d'unicite de UE.code, note au cas par cas ci-dessous) :
  - DCA3153 : "Droit constitutionnel approfondi" (M2 Droit public fondamental,
    CEC=5) vs "Droit civil approfondi" (M2 Droit prive fondamental, CEC=6).
    Le second est renomme DCA3153P.
  - DEN3141 : "Droit et environnement" (M1 Droit public fondamental, 2 ECUE,
    CEC=4) vs "Droit de l'environnement" (M1 Droit prive fondamental,
    1 ECUE, CEC=3). Le second est renomme DEN3141P.
  - LAN3141 : "Langues" (M1 Droit public fondamental, CEC=2) vs "Langues"
    (M1 Histoire du droit et des institutions, CEC=1). Le second est
    renomme LAN3141H.

Autres corrections de coquilles evidentes de la maquette source (motif
<code UE><rang> incoherent sinon) :
  - "TRI253" -> TRI3253, "SOR253" -> SOR3253 (Master 2 Science politique).
  - "MER3253" repete a l'identique pour les 2 ECUE de methodologie ->
    MER32531 / MER32532.
  - "DFA331531/32/33" (Master 2 Droit prive fondamental) conserve tel quel
    (motif different mais univoque, verifie cote fichier source).

SJP3153 ("Droits social ou judiciaire privé ou pénal", M2 Droit prive
fondamental) est une UE a choix (le nom contient "ou") : comme pour les UE
Optionnelles de M1 (DEN3141P / DFP3141), chacune des 3 ECUE est enregistree
avec son coefficient plein (2), le total officiel du semestre ne comptant
qu'un seul choix.

Le coefficient de l'UE (CEC) n'est jamais saisi ici : il est recalcule
automatiquement par UE.sync_coef_from_ecues() a partir de la somme des
coefficients ECUE (CECT), comme le fait deja apps/ue/models.py.

Usage :
  python manage.py seed_maquette_droit_m1_m2
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.models import ECUE, UE

FILIERE_NAME = "Sciences juridiques, administratives et politiques"

SPE_PUBLIC = "Droit public fondamental"
SPE_PRIVE = "Droit prive fondamental"
SPE_HISTOIRE = "Histoire du droit et des institutions"
SPE_SCIENCEPO = "Science politique"

# ---------------------------------------------------------------------------
# Donnees source (maquette UFR 2024-2025) — Master 1 et Master 2.
# Chaque bloc = (niveau, [noms_specialite existants], semestre [info/affichage
# seulement], liste d'UE).
# Chaque UE = (code, nom, [(code_ecue, nom_ecue, coef_ecue), ...]).
# ---------------------------------------------------------------------------

BLOCS = [
    # ================= MASTER 1 — Droit public fondamental =================
    ("M1", [SPE_PUBLIC], "S1", [
        ("DRE3141", "Droit de la régulation économique", [
            ("DRE31411", "Libertés économiques", 3),
            ("DRE31412", "Régulation sectorielle et transervale", 3),
        ]),
        ("CGP3141", "Contrôle de la gouvernance publique", [
            ("CGP31411", "Ethique et déontologie", 2),
            ("CGP31412", "Contrôle de la gouvernance financière", 2),
            ("CGP31413", "Droit constitutionnel et international pénal", 2),
        ]),
        ("FPA3141", "Droit de la fonction publique et science administrative", [
            ("FPA31411", "Science administrative", 2),
            ("FPA31412", "Fonction publique", 3),
        ]),
        ("DEN3141", "Droit et environnement", [
            ("DEN31411", "Droit de l'urbanisme et de la construction", 2),
            ("DEN31412", "Droit de l'environnement", 2),
        ]),
        ("DRD3141", "Droit de la représentation et démocratie", [
            ("DRD31411", "Droit électoral", 2),
            ("DRD31412", "Droit parlementaire", 1),
        ]),
        ("DCP3141", "Droit des contrats publics", [
            ("DCP31411", "Règles communes", 1),
            ("DCP31412", "Règles spéciales", 3),
        ]),
        ("LAN3141", "Langues", [
            ("LAN31411", "Langues", 2),
        ]),
    ]),
    ("M1", [SPE_PUBLIC], "S2", [
        ("DIE3142", "Droit international économique", [
            ("DIE31421", "Droit de l'OMC", 2),
            ("DIE31422", "Droit des investissements", 3),
        ]),
        ("CPN3142", "Contentieux de droit public national", [
            ("CPN31421", "Contentieux constitutionnel", 2),
            ("CPN31422", "Contentieux administratif", 2),
            ("CPN31423", "Contentieux financier et fiscal", 2),
        ]),
        ("COI3142", "Contentieux international", [
            ("COI31421", "Contentieux international général (CIJ, arbitrage)", 2),
            ("COI31422", "Contentieux spécial (CPI, TIDM)", 2),
            ("COI31423", "Contentieux international africain", 2),
        ]),
        ("GOE3142", "Gouvernance électorale", [
            ("GOE31421", "Géopolitique électorale", 2),
            ("GOE31422", "Contentieux électoral", 3),
        ]),
        ("DPS3142", "Droit international public spécial", [
            ("DPS31421", "Droit des organisations internationales", 2),
            ("DPS31422", "Relations diplomatiques", 2),
        ]),
        ("DAP3142", "Droit des activités portuaires et aéroportuaires", [
            ("DAP31421", "Droit des activités portuaires et aéroportuaires", 3),
        ]),
        ("INF3142", "Informatique", [
            # NOTE: CEC retrouve par recoupement avec le total du semestre (30).
            ("INF31421", "Informatique", 1),
        ]),
    ]),

    # ================= MASTER 1 — Droit prive fondamental =================
    ("M1", [SPE_PRIVE], "S1", [
        ("REM3141", "Régimes matrimoniaux", [
            ("REM31411", "Règles communes", 2),
            ("REM31412", "Règles spécifiques", 3),
        ]),
        ("CSP3141", "Contrats spéciaux", [
            ("CSP31411", "Contrats civils", 3),
            ("CSP31412", "Contrats commerciaux", 2),
        ]),
        ("IPC3141", "Instruments de paiement et de crédit", [
            ("IPC31411", "Les instruments classiques", 3),
            ("IPC31412", "Les instruments modernes", 2),
        ]),
        ("DPI3141", "Droit privé international", [
            # NOTE: la maquette source prefixe ces ECUE "DIN..." alors que
            # l'UE est codee "DPI3141". Conserve tel quel.
            ("DIN31411", "Droit international privé", 3),
            ("DIN31412", "Droit du commerce international", 2),
        ]),
        ("MEN3141", "Comptabilité, gestion et audit juridique", [
            ("MEN31411", "Comptabilité", 1),
            ("MEN31412", "Gestion", 1),
            ("MEN31413", "Audit juridique", 1),
        ]),
        ("DAA3141", "Droit des affaires approfondi", [
            ("DAA31411", "Banques", 1),
            ("DAA31412", "Transports et assurances", 2),
            ("DAA31413", "Propriété intellectuelle", 1),
        ]),
        ("DEN3141P", "Droit de l'environnement", [
            # NOTE: code source "DEN3141" en collision avec l'UE "Droit et
            # environnement" du parcours Droit public fondamental (contenu
            # different) — renomme DEN3141P. UE Optionnelle : alternative a
            # DFP3141, coefficient plein enregistre sur les deux.
            ("DEN31411", "Droit de l'environnement", 3),
        ]),
        ("DFP3141", "Droit de la fonction publique", [
            ("DFP31411", "Droit de la fonction publique", 3),
        ]),
    ]),
    ("M1", [SPE_PRIVE], "S2", [
        ("DSL3142", "Droit des successions et libéralités", [
            ("DSL31421", "Succesions", 3),
            ("DSL31422", "Libéralités", 2),
        ]),
        ("END3142", "Entreprises en difficulté", [
            ("END31421", "Prévention des difficultés", 3),
            ("END31422", "Traitement des difficultés", 3),
        ]),
        ("VEX3142", "Voies d'exécution", [
            ("VEX31421", "Règles générales", 2),
            ("VEX31422", "Règles particulières", 3),
        ]),
        ("DFA3142", "Droit fiscal des affaires", [
            ("DFA31421", "Droit fiscal des affaires", 4),
        ]),
        ("DPA3142", "Droit pénal approfondi", [
            ("DPA31421", "Droit pénal des affaires", 2),
            ("DPA31422", "Droit pénal spécial", 2),
        ]),
        ("ETA3142", "Ethique des affaires", [
            ("ETA31421", "Compliance", 2),
            ("ETA31422", "Ethique du management", 2),
        ]),
        ("OTE3142", "Outils techniques", [
            ("OTE31421", "Informatique", 1),
            ("OTE31422", "Anglais juridique", 1),
        ]),
    ]),

    # ========= MASTER 1 — Histoire du droit et des institutions =========
    ("M1", [SPE_HISTOIRE], "S1", [
        ("HDA3141", "Histoire du droit africain", [
            ("HDA31411", "Histoire du droit de l'environnement africain", 3),
            ("HDA31412", "Histoire des institutions publiques et privées africaines", 3),
        ]),
        ("HDC3141", "Histoire du droit civil", [
            ("HDC31411", "Histoire du droit de la famille", 3),
            ("HDC31412", "Histoire du droit des obligations", 3),
        ]),
        ("CSP3141", "Contrats spéciaux", [
            ("CSP31411", "Contrats civils", 3),
            ("CSP31412", "Contrats commerciaux", 2),
        ]),
        ("FPA3141", "Droit de la fonction publique et science administrative", [
            ("FPA31411", "Science administrative", 2),
            ("FPA31412", "Fonction publique", 3),
        ]),
        ("HPP3141", "Histoire des idées politiques", [
            ("HPP31411", "Histoire des idées politiques européennes", 2),
            ("HPP31412", "Histoire des idées politiques africaines", 2),
        ]),
        ("MIH3141", "Méthode d'interprétation des documents historiques", [
            ("MIH31411", "Méthode d'interprètation des documents historiques", 3),
        ]),
        ("LAN3141H", "Langues", [
            # NOTE: code source "LAN3141" en collision avec l'UE "Langues"
            # du parcours Droit public fondamental (coefficient different :
            # 1 ici contre 2 la-bas) — renomme LAN3141H.
            ("LAN31411", "Langues", 1),
        ]),
    ]),
    ("M1", [SPE_HISTOIRE], "S2", [
        ("HII3142", "Histoire des institutions publiques ivoiriennes", [
            ("HII31421", "Histoire des institutions politiques", 3),
            ("HII31422", "Histoire des institutions administratives et judiciaires", 3),
        ]),
        ("DCO3142", "Droit coutumier", [
            ("DCO31421", "Grands systèmes juridiques contemporains", 3),
            ("DCO31422", "droit coutumier africain", 3),
        ]),
        ("VEX3142", "Voies d'exécution", [
            ("VEX31421", "Règles générales", 2),
            ("VEX31422", "Règles particulières", 3),
        ]),
        ("DCP3142", "Droit des contrats publics", [
            ("DCP31421", "Règles communes", 1),
            ("DCP31422", "Règles spéciales", 3),
        ]),
        ("ANT3142", "Anthropologie", [
            ("ANT31421", "Anthropologie politique et juridique", 2),
            ("ANT31422", "Bioéthique", 1),
        ]),
        ("MEI3142", "Méthodologie d'enquêtes et d'interview", [
            ("MEI31421", "Méthode d'enquêtes de terrain", 2),
            ("MEI31422", "Méthode des interviews", 1),
        ]),
        ("CUG3142", "Culture générale", [
            ("CUG31421", "Légistique", 2),
            ("CUG31422", "Informatique", 1),
        ]),
    ]),

    # ================= MASTER 1 — Science politique =================
    # NOTE: dans la maquette source, le tableau de codes "...41" se termine
    # par "Total semestre 2" et celui de codes "...42" par "Total semestre
    # 1" (inversion visible dans le fichier). Le semestre indique ci-dessous
    # suit les libelles "Total semestre X" du fichier, sans consequence sur
    # les donnees enregistrees (aucun champ semestre n'existe en base).
    ("M1", [SPE_SCIENCEPO], "S2", [
        ("RED3241", "Relations diplomatiques", [
            ("RED32411", "Droit des relations diplomatiques", 3),
            ("RED32412", "Droit des agents diplomatiques", 3),
        ]),
        ("SDA3241", "Sécurité et développement en Afrique", [
            ("SDA32411", "Rôle de l'Union Africaine", 3),
            ("SDA32412", "Rôle de la CEDEAO", 3),
        ]),
        ("GCA3241", "Gestion des crises en Afrique", [
            ("GCA32411", "Gestion juridique des crises en Afrique", 3),
            ("GCA32412", "Gestion politique des crises en Afrique", 3),
        ]),
        ("PCO3241", "Politiques comparées", [
            ("PCO32411", "Grands concepts des politiques comparées", 2),
            ("PCO32412", "Méthodes de la politique comparée", 3),
        ]),
        ("TES3241", "Techniques d'enquêtes en sciences sociales", [
            ("TES32411", "Techniques d'enquêtes en sciences sociales", 3),
        ]),
        ("GDP3241", "Gestion de projets", [
            ("GDP32411", "Gestion de projets", 3),
        ]),
        ("INF3241", "Anglais", [
            ("INF32411", "Anglais", 1),
        ]),
    ]),
    ("M1", [SPE_SCIENCEPO], "S1", [
        ("RED3242", "Pratiques des relations diplomatiques", [
            ("RED32421", "Protocoles et usages diplomatiques", 3),
            ("RED32422", "Représentations diplomatiques et consulaires", 3),
        ]),
        ("PEC3242", "Politiques étrangères comparées", [
            ("PEC32421", "Politiques étrangères économiques comparées", 2),
            ("PEC32422", "Politiques étrangères culturelles comparées", 2),
        ]),
        ("ITP3242", "Idées et théories politiques en Afrique", [
            ("ITP32421", "Idées et théories politiques en Afrique précoloniale", 3),
            ("ITP32422", "Idees et théories politiques en Afrique postcoloniale", 2),
        ]),
        ("PGC3242", "Prévention et gestion des crises en Afrique", [
            ("PGC32421", "Médiation et conciliation", 3),
            ("PGC32422", "Lutte contre la criminalité transnationale organisée", 3),
        ]),
        ("SDS3242", "Stratégies de défense et sécurité", [
            ("SDS32421", "Stratégies classiques de défense et sécurité", 2),
            ("SDS32422", "Stratégies nouvelles de défense et sécurité", 2),
        ]),
        ("CAS3242", "Cartographie et analyse spatiale", [
            ("CAS32421", "Cartographie et analyse spatiale", 3),
        ]),
        ("INF3242", "Informatique", [
            ("INF32421", "Informatique", 2),
        ]),
    ]),

    # ================= MASTER 2 — Droit public fondamental =================
    ("M2", [SPE_PUBLIC], "S3", [
        ("TGD3153", "Théorie générale du droit", [
            ("TGD31531", "Normativité et personnalité juridique", 3),
            ("TGD31532", "Structure du droit", 2),
        ]),
        ("DCA3153", "Droit constitutionnel approfondi", [
            ("DCA31531", "Concepts fondamentaux", 3),
            ("DCA31532", "Principes fondamentaux des institutions", 2),
        ]),
        ("DAA3153", "Droit administratif approfondi", [
            ("DAA31531", "Service public", 3),
            ("DAA31532", "Puissance publique", 2),
        ]),
        ("IPA3153", "Droit international public approfondi", [
            ("IPA31531", "Reglement pacifique des différends", 3),
            ("IPA31532", "Reglement non pacifique des différends", 2),
        ]),
        ("DEF3153", "Droit public économique et financiers", [
            ("DEF31531", "Finances publiques approfondies", 3),
            ("DEF31532", "Droit public économique", 2),
        ]),
        ("MER3153", "Méthodologie de la recherche", [
            ("MER31531", "Recherche documentaire", 2),
            ("MER31532", "Analyse des données", 1),
        ]),
        ("ARO3153", "Art oratoire", [
            ("ARO31531", "Art oratoire", 2),
        ]),
    ]),
    ("M2", [SPE_PUBLIC], "S4", [
        ("MEM3154", "Mémoire", [
            ("MEM31541", "Redaction du mémoire", 15),
            ("MEM31542", "Soutenance du mémoire", 15),
        ]),
    ]),

    # ================= MASTER 2 — Droit prive fondamental =================
    ("M2", [SPE_PRIVE], "S3", [
        ("TGD3153", "Théorie générale du droit", [
            ("TGD31531", "Normativité et personnalité juridique", 3),
            ("TGD31532", "Structure du droit", 2),
        ]),
        ("DCA3153P", "Droit civil approfondi", [
            # NOTE: code source "DCA3153" en collision avec l'UE "Droit
            # constitutionnel approfondi" du parcours Droit public
            # fondamental (contenu different) — renomme DCA3153P.
            ("DCA31531", "Droit des personnes", 3),
            ("DCA31532", "Droit des obligations", 3),
        ]),
        ("DCM3153", "Droit commercial approfondi", [
            ("DCM31531", "Droit commercial général", 3),
            ("DCM31532", "Droits des sociétés", 3),
        ]),
        ("DFA3153", "Droit privé fondamental approfondi", [
            ("DFA331531", "Droit civil", 2),
            ("DFA331532", "Droit commercial", 2),
            ("DFA331533", "Droit international privé", 2),
        ]),
        ("SJP3153", "Droits social ou judiciaire privé ou pénal", [
            # UE a choix ("ou" dans le nom) : chaque ECUE porte son
            # coefficient plein, un seul est compte dans le total officiel.
            ("SJP31531", "Droit social", 2),
            ("SJP31532", "Droit judiciaire privé", 2),
            ("SJP31533", "Droit pénal", 2),
        ]),
        ("MER3153", "Méthodologie de la recherche", [
            ("MER31531", "Recherche documentaire", 2),
            ("MER31532", "Analyse des données", 1),
        ]),
        ("ARO3153", "Art oratoire", [
            ("ARO31531", "Art oratoire", 2),
        ]),
    ]),
    ("M2", [SPE_PRIVE], "S4", [
        ("MEM3154", "Mémoire", [
            ("MEM31541", "Redaction du mémoire", 15),
            ("MEM31542", "Soutenance du mémoire", 15),
        ]),
    ]),

    # ========= MASTER 2 — Histoire du droit et des institutions =========
    ("M2", [SPE_HISTOIRE], "S3", [
        ("TGD3153", "Théorie générale du droit", [
            ("TGD31531", "Normativité et personnalité juridique", 3),
            ("TGD31532", "Structure du droit", 2),
        ]),
        ("CJC3153", "Culture juridique et droit comparé", [
            ("CJC31531", "Histoire du droit de la famille approfondie", 3),
            ("CJC31532", "Histoire approfondie du droit pénal approfondie", 2),
        ]),
        ("ACI3153", "Approche comparative des institutions", [
            ("ACI31531", "Histoire des institutions de l'Egypte pharaonique approfondie", 3),
            ("ACI31532", "Histoire des institutions publiques et privées de l'Afrique approfondie", 2),
        ]),
        ("PJU3153", "Pensée juridique", [
            ("PJU31531", "Histoire de la pensée juridique", 1),
            ("PJU31532", "Analyse idéologique des concepts juridiques", 2),
            ("PJU31533", "Histoire des relations internationales approfondies", 2),
        ]),
        ("HOB3153", "Histoire du droit des obligations, des biens et des affaires", [
            ("HOB31531", "Histoire du droit des obligations approfondie", 2),
            ("HOB31532", "Histoire du droit des affaires approfondie", 2),
            ("HOB31533", "Histoire du droit des biens approfondie", 1),
        ]),
        ("MER3153", "Méthodologie de la recherche", [
            ("MER31531", "Recherche documentaire", 2),
            ("MER31532", "Analyse des données", 1),
        ]),
        ("ARO3153", "Art oratoire", [
            ("ARO31531", "Art oratoire", 2),
        ]),
    ]),
    ("M2", [SPE_HISTOIRE], "S4", [
        ("MEM3154", "Mémoire", [
            ("MEM31541", "Redaction du mémoire", 15),
            ("MEM31542", "Soutenance du mémoire", 15),
        ]),
    ]),

    # ================= MASTER 2 — Science politique =================
    ("M2", [SPE_SCIENCEPO], "S3", [
        ("TSP3253", "Théorie de la science politique", [
            ("TSP32531", "Ontologie de la science politique", 2),
            ("TSP32532", "Épistémologie de la science politique", 2),
        ]),
        ("TRI3253", "Théories des relations internationales", [
            # NOTE: code source "TRI253" — corrige en TRI3253 (motif <code
            # UE><rang> sinon incoherent avec toutes les autres UE).
            ("TRI32531", "Relations internationales", 2),
            ("TRI32532", "Théories des relations internationales: Réalisme", 2),
            ("TRI32533", "Théories des relations internationales: Libéralisme", 2),
        ]),
        ("GEO3253", "Géopolitique", [
            ("GEO32531", "Organisations régionales et géopolitique", 2),
            ("GEO32532", "Géopolitique de l'Afrique", 2),
            ("GEO32533", "Afrique dans la géopolitique mondiale", 2),
        ]),
        ("GOD3253", "Gouvernance et diplomatie", [
            ("GOD32531", "Gouvernance du développement", 2),
            ("GOD32532", "Théories de la diplomatie africaine", 2),
            ("GOD32533", "Systèmes de gouvernance", 2),
        ]),
        ("SOR3253", "Sociologie des relations internationales", [
            # NOTE: code source "SOR253" — corrige en SOR3253.
            ("SOR32531", "Sociologie des relations interntaionales", 2),
            ("SOR32532", "Sociologie des relations internationales en Afrique", 2),
            ("SOR32533", "Grands thèmes de sociologie des relations internationales globales", 2),
        ]),
        ("MER3253", "Méthodologie", [
            # NOTE: la maquette source repete le meme code ECUE "MER3253"
            # pour les 2 lignes — corrige en MER32531 / MER32532.
            ("MER32531", "Recherche documentaire", 1),
            ("MER32532", "Analyse de données", 1),
        ]),
    ]),
    ("M2", [SPE_SCIENCEPO], "S4", [
        ("MEM3254", "Mémoire", [
            ("MEM32541", "Redaction du mémoire", 15),
            ("MEM32542", "Soutenance du mémoire", 15),
        ]),
    ]),
]


class Command(BaseCommand):
    help = (
        "Seed le catalogue UE/ECUE des Master 1 et Master 2 (4 parcours) "
        "a partir de la maquette UFR 2024-2025."
    )

    def handle(self, *args, **options):
        filiere = Filiere.objects.get(name=FILIERE_NAME)
        self.stdout.write(f"Filière {FILIERE_NAME} — existante")

        with transaction.atomic():
            for niveau_code, noms_specialites, semestre, ues in BLOCS:
                niveau, n_created = Niveau.objects.get_or_create(
                    filiere=filiere, name=niveau_code
                )
                self.stdout.write(
                    f"\n{niveau_code} {semestre} — niveau {'créé' if n_created else 'existant'}"
                )

                specialites = []
                for nom_spe in noms_specialites:
                    specialite, s_created = Specialite.objects.get_or_create(
                        name=nom_spe, niveau=niveau
                    )
                    specialites.append(specialite)
                    self.stdout.write(
                        f"  Spécialité « {nom_spe} » — "
                        f"{'créée' if s_created else 'existante'}"
                    )

                for code_ue, nom_ue, ecues in ues:
                    ue, ue_created = UE.objects.get_or_create(
                        code=code_ue, defaults={"name": nom_ue}
                    )
                    if not ue_created and ue.name != nom_ue:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [ATTENTION] UE {code_ue} existe déjà avec un nom "
                                f"différent (« {ue.name} » vs « {nom_ue} »). Nom "
                                f"existant conservé, ECUE quand même rattachées."
                            )
                        )
                    ue.specialites.add(*specialites)

                    self.stdout.write(
                        f"    UE {code_ue} — {nom_ue} — "
                        f"{'créée' if ue_created else 'existante'}"
                    )

                    for code_ecue, nom_ecue, coef in ecues:
                        ecue, ecue_created = ECUE.objects.get_or_create(
                            ue=ue,
                            code=code_ecue,
                            defaults={"name": nom_ecue, "coef": coef},
                        )
                        self.stdout.write(
                            f"      └─ ECUE {code_ecue} — {nom_ecue} "
                            f"(CECT={coef}) — {'créée' if ecue_created else 'existante'}"
                        )

        self.stdout.write(self.style.SUCCESS("\n✅  Maquette Droit M1-M2 importée."))
        self._controle_integrite()

    def _controle_integrite(self):
        """Petit contrôle de cohérence après import (lecture seule)."""
        self.stdout.write("\n" + "─" * 60)
        self.stdout.write("CONTRÔLE D'INTÉGRITÉ")
        self.stdout.write("─" * 60)

        ue_sans_ecue = list(UE.objects.filter(ecues__isnull=True).values_list("code", flat=True))
        if ue_sans_ecue:
            self.stdout.write(self.style.WARNING(f"UE sans ECUE (toute la base) : {ue_sans_ecue}"))
        else:
            self.stdout.write("Aucune UE sans ECUE.")

        self.stdout.write(self.style.SUCCESS("Contrôle terminé."))
