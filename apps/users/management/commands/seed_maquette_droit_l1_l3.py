"""
Seed du catalogue pedagogique (UE/ECUE) de la filiere Droit — Licence 1, 2, 3,
a partir de la maquette UFR Sciences Juridiques, Administratives et
Politiques 2024-2025.

Perimetre : Licence 1, Licence 2, Licence 3 (parcours "Droit Public, Droit
Prive et Histoire du Droit" et parcours "Science Politique"). Les Master 1/2
ne sont pas inclus : hors perimetre de la demande initiale, et la maquette
source reutilise certains codes UE entre parcours de Master avec un contenu
different (ex: DEN3141 designe une UE differente selon le parcours) — ce qui
casserait la contrainte d'unicite de UE.code. A nettoyer cote fichier source
avant un import Master.

"Licence 3 Sciences professionnelles" n'existe pas dans cette maquette : les
deux parcours reels de L3 sont "Droit Public, Droit Prive et Histoire du
Droit" et "Science Politique".

Filiere et specialites : la base contient deja la filiere "Sciences
juridiques, administratives et politiques" (choisie par l'utilisateur parmi
plusieurs filieres "Droit"/"Droits" existantes) avec des Niveau L1-M2 et des
Specialite deja crees. Ce script reutilise ces objets existants (get_or_create
par nom exact) au lieu d'en creer de nouveaux :
  - L1, L2  -> Specialite "Tronc commun" (deja presente, pas de parcours
    nomme dans la maquette a ce niveau).
  - L3 parcours "Droit Public, Droit Prive et Histoire du Droit" -> la base
    a 3 specialites separees ("Droit public", "Droit prive", "Histoire du
    droit") plutot qu'une specialite combinee. La maquette presente ces UE
    comme un tronc commun a ce stade (la specialisation reelle n'apparait
    qu'a partir du Master), donc chaque UE de ce bloc est rattachee aux 3
    specialites en meme temps (ManyToMany) — decision validee avec
    l'utilisateur.
  - L3 parcours "Science Politique" -> Specialite "Science politique" (deja
    presente).
Les noms de specialite ci-dessus reprennent l'orthographe exacte deja en
base (ex. "Droit prive" sans accent) pour eviter de creer un doublon.

Le coefficient de l'UE (CEC) n'est jamais saisi ici : il est recalcule
automatiquement par UE.sync_coef_from_ecues() a partir de la somme des
coefficients ECUE (CECT), comme le fait deja apps/ue/models.py a chaque
creation d'ECUE.

Usage :
  python manage.py seed_maquette_droit_l1_l3
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.filiere.models import Filiere
from apps.niveau.models import Niveau
from apps.specialites.models import Specialite
from apps.ue.models import ECUE, UE

FILIERE_NAME = "Sciences juridiques, administratives et politiques"

# ---------------------------------------------------------------------------
# Donnees source (maquette UFR 2024-2025).
#
# Chaque bloc = (niveau, [noms_specialite existants], semestre [info/affichage
# seulement, non stocke en base — aucun champ "semestre" n'existe sur UE ni
# ECUE], liste d'UE).
# Chaque UE = (code, nom, [(code_ecue, nom_ecue, coef_ecue), ...]).
#
# Une UE peut etre rattachee a plusieurs specialites en meme temps (cas du
# tronc commun L3 "Droit", cf. docstring du module).
# ---------------------------------------------------------------------------

BLOCS = [
    # ================= LICENCE 1 =================
    ("L1", ["Tronc commun"], "S1", [
        ("IND3101", "Introduction au droit", [
            ("IND31011", "Droit objectif", 3),
            ("IND31012", "Droit subjectif", 2),
        ]),
        ("ISP3101", "Introduction à la science politique", [
            ("ISP31011", "Histoire de la science politique", 3),
            ("ISP31012", "Grands concepts de la science politique", 2),
        ]),
        ("DCO3101", "Droit constitutionnel", [
            ("DCO31011", "Théorie générale de l'Etat", 3),
            ("DCO31012", "Théorie générale de la Constitution", 2),
        ]),
        ("DCP3101", "Droit civil des personnes", [
            ("DCP31011", "Personnes physiques", 4),
            ("DCP31012", "Personnes morales", 1),
        ]),
        ("HDA3101", "Introduction historique au droit africain", [
            ("HDA31011", "Droit historique des sociétés anétatiques", 2),
            ("HDA31012", "Droit historique des sociétés politiques", 2),
        ]),
        ("MJU3101", "Méthodologie juridique", [
            ("MJU31011", "Méthodologie de la recherche documentaire et des exercices juridiques", 2),
            ("MJU31012", "Techniques d'expression juridique", 1),
        ]),
        ("ACE3101", "Arts, cultures, Economie politique", [
            ("ACE31011", "Economie politique", 2),
            ("ACE31012", "Arts et Cultures", 1),
        ]),
    ]),
    ("L1", ["Tronc commun"], "S2", [
        ("DCO3102", "Droit constitutionnel", [
            ("DCO31021", "Typologie des régimes et système des partis politiques", 4),
            ("DCO31022", "Régime politique ivoirien", 2),
        ]),
        ("DCF3102", "Droit civil de la famille", [
            ("DCF31021", "Unions civiles", 4),
            ("DCF31022", "Filiations", 2),
        ]),
        ("HIM3102", "Histoire des institutions des civilisations méditerranéennes", [
            ("HIM31021", "Institutions médittéranéennes", 3),
            ("HIM31022", "Droit romain", 2),
        ]),
        ("OJP3102", "Organisation juridictionnelle et politique de la Côte d'Ivoire", [
            ("OJP31021", "Organisation juridictionnelle", 4),
            ("OJP31022", "Organisation politique", 1),
        ]),
        ("ICO3102", "Institutions communautaires", [
            ("ICO31021", "Institutions communautaires", 3),
        ]),
        ("DHL3102", "Initiation aux droits de l'homme et aux libertés publiques", [
            ("DHL31021", "Droits de l'Homme", 2),
            ("DHL31022", "Droits des libertés publiques", 1),
        ]),
        ("TEF3102", "Techniques d'expression française", [
            ("TEF31021", "Techniques d'expression française", 2),
        ]),
    ]),

    # ================= LICENCE 2 =================
    ("L2", ["Tronc commun"], "S3", [
        ("OAA3103", "L'organisation et l'action de l'administration", [
            ("OAA31031", "Organisation de l'administration", 3),
            ("OAA31032", "Action de l'administration", 2),
        ]),
        ("ACJ3103", "L'acte juridique", [
            ("ACJ31031", "Contrat", 3),
            ("ACJ31032", "autres actes juridiques", 2),
        ]),
        ("DPG3103", "Droit pénal général", [
            ("DPG31031", "Infraction", 3),
            ("DPG31032", "Répression", 2),
        ]),
        ("HIC3103", "Histoire des institutions coloniales", [
            ("HIC31031", "Histoire des institutions publiques africaines", 2),
            ("HIC31032", "Histoire des institutions privées africaines", 2),
        ]),
        ("DFI3103", "Droit financier", [
            ("DFI31031", "Droit public financier", 3),
            ("DFI31032", "Droit privé financier", 3),
        ]),
        ("PRD3103", "Pratique du droit", [
            ("PRD31031", "Initiation à la rédaction d'actes juridiques", 2),
            ("PRD31032", "Visites des institutions", 1),
        ]),
        ("MOM3103", "Management des organisations et Marketing digital", [
            ("MOM31031", "Management des organisations", 1),
            ("MOM31032", "Marketing digital", 1),
        ]),
    ]),
    ("L2", ["Tronc commun"], "S4", [
        ("CAD3104", "Le contrôle de l'administration", [
            ("CAD31041", "La responsabilité de l'administration", 3),
            ("CAD31042", "Le recours pour excès de pouvoir", 3),
        ]),
        ("FJU3104", "Le fait juridique", [
            # NOTE: la maquette source ecrit "FJU431041" pour cette ECUE.
            # Corrige en FJU31041 : coquille evidente, tous les autres codes
            # ECUE du document suivent le motif <code UE><rang>.
            ("FJU31041", "Responsabilité civile", 4),
            ("FJU31042", "Quasi-contrats", 2),
        ]),
        ("DPR3104", "Droit processuel", [
            ("DPR31041", "Procédure pénale", 3),
            ("DPR31042", "Procédure civile, commerciale et administrative", 3),
        ]),
        ("AJP3104", "Anthropologie juridique et politique", [
            ("AJP31041", "Anthropologie juridique", 2),
            ("AJP31042", "Anthropologie politique", 2),
        ]),
        ("LEG3104", "Légistique", [
            ("LEG31041", "Légistique des actes législatifs", 2),
            ("LEG31042", "Légistique des actes règlementaires", 2),
        ]),
        ("DEN3104", "Droit de l'environnement", [
            ("DEN31041", "Initiation au droit de l'environnement", 2),
        ]),
        ("IGE3104", "Introduction à la géopolitique", [
            ("IGE31041", "Géopolitique des blocs régionaux", 1),
            ("IGE31042", "Géopolitique des mers et des océans", 1),
        ]),
    ]),

    # ===== LICENCE 3 — Parcours Droit Public, Droit Prive et Histoire du Droit =====
    ("L3", ["Droit public", "Droit prive", "Histoire du droit"], "S5", [
        ("DIP3105", "Droit international public", [
            ("DIP31051", "Sources du Droit international public", 2),
            ("DIP31052", "Sujets du Droit international public", 3),
        ]),
        ("DCO3105", "Droit commercial", [
            ("DCO31051", "Acteurs du commerce", 2),
            ("DCO31052", "Moyens du commerce", 3),
        ]),
        ("CMO3105", "Circulation et modalités de l'obligation", [
            ("CMO31051", "Circulation de l'obligation", 2),
            ("CMO31052", "Modalités de l'obligation", 2),
        ]),
        ("DTR3105", "Droit du Travail", [
            ("DTR31051", "Relations individuelles", 2),
            ("DTR31052", "Relations collectives", 2),
        ]),
        ("DDC3105", "Droit du contentieux", [
            ("DDC31051", "Contentieux public", 2),
            ("DDC31052", "Contentieux privé", 2),
        ]),
        ("DAB3105", "Droit administratif des biens", [
            # NOTE: la maquette source prefixe ces ECUE "DCB..." alors que
            # l'UE est codee "DAB3105". Conserve tel quel — a verifier cote
            # fichier source.
            ("DCB31051", "Domaines", 3),
            ("DCB31052", "Expropriation et travaux publics", 3),
        ]),
        ("JSG3105", "Anglais juridique et gouvernance", [
            ("JSG31051", "Aspects juridiques et politiques de la gouvernance", 1),
            ("JSG31052", "Anglais juridique", 1),
        ]),
    ]),
    ("L3", ["Droit public", "Droit prive", "Histoire du droit"], "S6", [
        ("DEC3106", "Droit des espaces et du contentieux internationaux publics", [
            ("DEC31061", "Droit des espaces internationaux", 2),
            ("DEC31062", "Responsabilité et règlements des conflits internationaux", 3),
        ]),
        ("EXO3106", "Extinction des obligations", [
            ("EXO31061", "Extinction par l'exécution de l'obligation", 3),
            ("EXO31062", "Extinction sans exécution de l'obligation", 2),
        ]),
        ("DSG3106", "Droit des sociétés commerciales et du GIE", [
            ("DSG31061", "Droit commun des sociétés commerciales et du GIE", 3),
            ("DSG31062", "Droit spécial des sociétés commerciales et du GIE", 2),
        ]),
        ("DCB3106", "Droit civil des biens", [
            ("DCB31061", "Propriété", 2),
            ("DCB31062", "Démembrements de la propriété", 2),
        ]),
        ("IIP3106", "Histoire des institutions et idées politiques", [
            ("IIP31061", "Institutions politiques", 2),
            ("IIP31062", "Idées politiques", 2),
        ]),
        ("DSS3106", "Droit de la sécurité sociale et de la santé", [
            ("DSS31061", "Droit de la sécurité sociale", 2),
            ("DSS31062", "Droit de la santé", 1),
        ]),
        ("DFH3106", "Droit foncier et société humaine", [
            ("DFH31061", "Foncier rural et urbain", 2),
            ("DFH31062", "Droit des collectivités territoriales", 1),
            ("DFH31063", "Droit de la communication et du numérique", 1),
        ]),
    ]),

    # ================= LICENCE 3 — Parcours Science Politique =================
    ("L3", ["Science politique"], "S5", [
        ("SPD3235", "Systèmes politiques démocratiques", [
            ("SPD32351", "Systèmes politiques démocratiques en Afrique", 3),
            ("SPD32352", "Systèmes politiques démocratiques dans le reste du monde", 2),
        ]),
        ("SPO3235", "Sociologie politique", [
            ("SPO32351", "Grands courants de la sociologie politique", 3),
            ("SPO32352", "Analyse politique de l'État en Afrique", 3),
        ]),
        ("TRI3235", "Théories des relations internationales", [
            ("TRI32351", "Théories dominantes des relations internationales", 3),
            ("TRI32352", "Théories mineures des relations internationales", 2),
        ]),
        ("PPU3235", "Politiques publiques", [
            ("PPU32351", "Grands concepts des politiques publiques", 3),
            ("PPU32352", "Gouvernance multi-niveaux", 3),
        ]),
        ("CPD3235", "Coopération et politique de développement", [
            ("CPD32351", "Coopération bilatérale et multilatérale", 2),
            ("CPD32352", "Politique de développement", 2),
        ]),
        ("GPR3235", "Gestion de projets", [
            ("GPR32351", "Rédaction de projets", 1),
            ("GPR32352", "Mise en œuvre de projets", 1),
        ]),
        ("ANG3235", "Anglais", [
            # NOTE: ligne ambigue dans la maquette source ; coefficient
            # retrouve par recoupement avec le total du semestre (30 CEC).
            ("ANG32351", "Anglais", 2),
        ]),
    ]),
    ("L3", ["Science politique"], "S6", [
        ("ICC3236", "Identités, cultures et civilisations", [
            ("ICC32361", "Représentations de l'identité", 4),
            ("ICC32362", "Cultures et civilisations", 2),
        ]),
        ("SIN3236", "Sécurité internationale", [
            ("SIN32361", "Rôle de l'ONU", 3),
            ("SIN32362", "Rôle des organisations régionales et sous-régionales", 3),
        ]),
        ("SPA3236", "Systèmes politiques africains", [
            ("SPA32361", "Systèmes politiques étrangers", 3),
            ("SPA32362", "Système politique ivoirien", 3),
        ]),
        ("GER3236", "Géopolitique des espaces régionaux", [
            ("GER32361", "Espace terrestre", 2),
            ("GER32362", "Espace maritime", 2),
        ]),
        ("MRE3236", "Méthodologie de la recherche", [
            ("MRE32361", "Méthodologie de la recherche et de la rédaction du mémoire", 3),
        ]),
        ("TSS3236", "Techniques d'enquêtes en sciences sociales", [
            ("TSS32361", "Techniques d'enquêtes en sciences sociales", 3),
        ]),
        ("INF3236", "Informatique", [
            ("INF32361", "Informatique", 2),
        ]),
    ]),
]


class Command(BaseCommand):
    help = (
        "Seed le catalogue UE/ECUE de la filiere Droit (Licence 1, 2, 3) "
        "a partir de la maquette UFR 2024-2025."
    )

    def handle(self, *args, **options):
        filiere, created = Filiere.objects.get_or_create(name=FILIERE_NAME)
        self.stdout.write(f"Filière {FILIERE_NAME} — {'créée' if created else 'existe déjà'}")

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

        self.stdout.write(self.style.SUCCESS("\n✅  Maquette Droit L1-L3 importée."))
        self._controle_integrite()

    def _controle_integrite(self):
        """Petit contrôle de cohérence après import (lecture seule)."""
        self.stdout.write("\n" + "─" * 60)
        self.stdout.write("CONTRÔLE D'INTÉGRITÉ")
        self.stdout.write("─" * 60)

        codes_vus = [code for _, _, _, ues in BLOCS for code, _, _ in ues]
        doublons = sorted({c for c in codes_vus if codes_vus.count(c) > 1})
        if doublons:
            self.stdout.write(self.style.WARNING(f"Codes UE réutilisés dans la maquette : {doublons}"))
        else:
            self.stdout.write("Aucun doublon de code UE dans le périmètre importé.")

        ue_sans_ecue = list(UE.objects.filter(ecues__isnull=True).values_list("code", flat=True))
        if ue_sans_ecue:
            self.stdout.write(self.style.WARNING(f"UE sans ECUE (toute la base) : {ue_sans_ecue}"))
        else:
            self.stdout.write("Aucune UE sans ECUE.")

        self.stdout.write(self.style.SUCCESS("Contrôle terminé."))
