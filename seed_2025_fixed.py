"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — fixtures/seed_2025.py
 Données de test 2025 — Licence (tronc commun) + Masters spécialisés + Doctorat
 
 Commande : python manage.py shell < fixtures/seed_2025.py
            ou appeler seed_all() depuis le shell Django
=============================================================================
"""

import uuid
from datetime import timedelta, datetime
from django.utils import timezone
from django.contrib.auth.hashers import make_password


def seed_all():
    seed_filieres_niveaux()
    seed_ues_ecues()
    seed_utilisateurs()
    seed_documents()
    seed_consultations_favoris()
    print("\n✅ SEED 2025 TERMINÉ AVEC SUCCÈS !\n")


# =============================================================================
# 🏫  1. FILIÈRES & NIVEAUX
# =============================================================================

def seed_filieres_niveaux():
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("📚 Création filières & niveaux...")

    # ── Filière Tronc Commun (L1/L2/L3) ───────────────────────────────
    filiere_tc, _ = Filiere.objects.get_or_create(
        name="Droit (Tronc Commun)",
        defaults={'id': uuid.UUID('aaaaaaaa-0001-0001-0001-000000000001')}
    )

    # ──── Niveaux Licence (Tronc Commun) ───────────────────────────────────────
    niveaux_tc = {}
    for n in ['L1', 'L2', 'L3']:
        obj, _ = Niveau.objects.get_or_create(
            filiere=filiere_tc, name=n
        )
        niveaux_tc[n] = obj

    # ── Filières Master (Spécialisées) ──────────────────────────────────────────
    specialites_master = [
        {"name": "Droit des Contentieux", "id": "aaaaaaaa-0001-0001-0001-000000000002"},
        {"name": "Droit des Affaires", "id": "aaaaaaaa-0001-0001-0001-000000000003"},
        {"name": "Droit Public", "id": "aaaaaaaa-0001-0001-0001-000000000004"},
        {"name": "Droit Privé", "id": "aaaaaaaa-0001-0001-0001-000000000005"},
    ]

    filieres_master = {}
    niveaux_master = {}
    
    for spec in specialites_master:
        filiere, _ = Filiere.objects.get_or_create(
            name=spec["name"],
            defaults={'id': uuid.UUID(spec["id"])}
        )
        filieres_master[spec["name"]] = filiere
        
        # Créer M1 et M2 pour chaque spécialité
        for n in ['M1', 'M2']:
            niveau_key = f"{spec['name']}_{n}"
            obj, _ = Niveau.objects.get_or_create(
                filiere=filiere, name=n
            )
            niveaux_master[niveau_key] = obj

    # ── Filière Doctorat ───────────────────────────────────────────────────────
    filiere_doctorat, _ = Filiere.objects.get_or_create(
        name="Doctorat",
        defaults={'id': uuid.UUID('aaaaaaaa-0001-0001-0001-000000000006')}
    )
    
    doctorat, _ = Niveau.objects.get_or_create(
        filiere=filiere_doctorat, name="DOCTORAT"
    )

    print(f"   ✔ Filière Tronc Commun : {filiere_tc.name}")
    print(f"   ✔ Niveaux Licence : {', '.join(niveaux_tc.keys())}")
    print(f"   ✔ Filières Master : {', '.join(filieres_master.keys())}")
    print(f"   ✔ Niveaux Master : M1, M2 pour chaque spécialité")
    print(f"   ✔ Filière Doctorat : {filiere_doctorat.name}")
    
    return {
        'filiere_tc': filiere_tc,
        'niveaux_tc': niveaux_tc,
        'filieres_master': filieres_master,
        'niveaux_master': niveaux_master,
        'filiere_doctorat': filiere_doctorat,
        'doctorat': doctorat
    }


# =============================================================================
# 📖  2. UEs & ECUEs (issues des images)
# =============================================================================

def seed_ues_ecues():
    from apps.ue.models import UE, ECUE
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n📖 Création UEs & ECUEs 2025...")

    # ── Récupérer la structure ─────────────────────────────────────────────────
    filiere_tc = Filiere.objects.get(name="Droit (Tronc Commun)")
    filieres_master = {
        "Droit des Contentieux": Filiere.objects.get(name="Droit des Contentieux"),
        "Droit des Affaires": Filiere.objects.get(name="Droit des Affaires"),
        "Droit Public": Filiere.objects.get(name="Droit Public"),
        "Droit Privé": Filiere.objects.get(name="Droit Privé"),
    }
    
    niveaux_tc = {
        'L1': Niveau.objects.get(filiere=filiere_tc, name='L1'),
        'L2': Niveau.objects.get(filiere=filiere_tc, name='L2'),
        'L3': Niveau.objects.get(filiere=filiere_tc, name='L3'),
    }
    
    niveaux_master = {}
    for spec_name, filiere in filieres_master.items():
        niveaux_master[f"{spec_name}_M1"] = Niveau.objects.get(filiere=filiere, name='M1')
        niveaux_master[f"{spec_name}_M2"] = Niveau.objects.get(filiere=filiere, name='M2')

    # ── UEs Tronc Commun ───────────────────────────────────────────────────────
    ues_tc = [
        # L1
        {'code': 'DGL101', 'name': 'Droit Constitutionnel Général', 'niveaux': [niveaux_tc['L1']]},
        {'code': 'DGL102', 'name': 'Droit Civil des Personnes', 'niveaux': [niveaux_tc['L1']]},
        {'code': 'DGL103', 'name': 'Droit Penal Général', 'niveaux': [niveaux_tc['L1'], niveaux_tc['L2']]},
        {'code': 'DGL104', 'name': 'Introduction au Droit Administratif', 'niveaux': [niveaux_tc['L1']]},
        # L2
        {'code': 'DGL105', 'name': 'Histoire du Droit', 'niveaux': [niveaux_tc['L2'], niveaux_tc['L3']]},
        {'code': 'DGL106', 'name': 'Droit des Obligations', 'niveaux': [niveaux_tc['L2'], niveaux_tc['L3']]},
        # L3
        {'code': 'DGL107', 'name': 'Droit Constitutionnel Ivoirien', 'niveaux': [niveaux_tc['L3']]},
        {'code': 'DGL108', 'name': 'Droit Administratif Général', 'niveaux': [niveaux_tc['L3']]},
    ]

    # ── UEs Master Droit des Contentieux ───────────────────────────────────────────
    ues_contentieux = [
        # M1
        {'code': 'COC2102', 'name': 'Contentieux constitutionnel', 'niveaux': [niveaux_master["Droit des Contentieux_M1"]]},
        {'code': 'COA2101', 'name': 'Contentieux administratif', 'niveaux': [niveaux_master["Droit des Contentieux_M1"]]},
        {'code': 'CCI2103', 'name': 'Contentieux civil', 'niveaux': [niveaux_master["Droit des Contentieux_M1"]]},
        {'code': 'COF2104', 'name': 'Contentieux fiscal', 'niveaux': [niveaux_master["Droit des Contentieux_M1"]]},
        {'code': 'CPN2105', 'name': 'Contentieux pénal', 'niveaux': [niveaux_master["Droit des Contentieux_M1"]]},
        # M2
        {'code': 'CIP2201', 'name': 'Contentieux international public', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'CIE2202', 'name': 'Contentieux international économique', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'CCM2203', 'name': 'Contentieux commercial', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'VEX2204', 'name': 'Voies d\'exécution et procédure d\'urgence', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'DPR2206', 'name': 'Droit de la preuve', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'CPB2301', 'name': 'Contentieux interne public spécialisé', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'CIS2302', 'name': 'Contentieux international spécialisé', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'DER2303', 'name': 'Droit de l\'arbitrage', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'DIC2304', 'name': 'Contentieux international pénal', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'RAC2305', 'name': 'Rédaction d\'actes', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
        {'code': 'TCC2307', 'name': 'Mémoire', 'niveaux': [niveaux_master["Droit des Contentieux_M2"]]},
    ]

    # ── UEs Master Droit des Affaires ───────────────────────────────────────────────
    ues_affaires = [
        # M1
        {'code': 'DAC3101', 'name': 'Droit des Sociétés', 'niveaux': [niveaux_master["Droit des Affaires_M1"]]},
        {'code': 'DAC3102', 'name': 'Droit Commercial Général', 'niveaux': [niveaux_master["Droit des Affaires_M1"]]},
        {'code': 'DAC3103', 'name': 'Droit Bancaire et Financier', 'niveaux': [niveaux_master["Droit des Affaires_M1"]]},
        {'code': 'DAC3104', 'name': 'Droit Fiscal des Entreprises', 'niveaux': [niveaux_master["Droit des Affaires_M1"]]},
        {'code': 'DAC3105', 'name': 'Droit de la Concurrence', 'niveaux': [niveaux_master["Droit des Affaires_M1"]]},
        # M2
        {'code': 'DAC3201', 'name': 'Droit International des Affaires', 'niveaux': [niveaux_master["Droit des Affaires_M2"]]},
        {'code': 'DAC3202', 'name': 'Droit Boursier et Marchés Financiers', 'niveaux': [niveaux_master["Droit des Affaires_M2"]]},
        {'code': 'DAC3203', 'name': 'Propriété Intellectuelle', 'niveaux': [niveaux_master["Droit des Affaires_M2"]]},
        {'code': 'DAC3204', 'name': 'Droit des Nouvelles Technologies', 'niveaux': [niveaux_master["Droit des Affaires_M2"]]},
        {'code': 'TDA3205', 'name': 'Mémoire Droit des Affaires', 'niveaux': [niveaux_master["Droit des Affaires_M2"]]},
    ]

    # ── UEs Master Droit Public ───────────────────────────────────────────────────
    ues_public = [
        # M1
        {'code': 'DPB4101', 'name': 'Droit Administratif Approfondi', 'niveaux': [niveaux_master["Droit Public_M1"]]},
        {'code': 'DPB4102', 'name': 'Droit Constitutionnel Comparé', 'niveaux': [niveaux_master["Droit Public_M1"]]},
        {'code': 'DPB4103', 'name': 'Droit des Libertés Fondamentales', 'niveaux': [niveaux_master["Droit Public_M1"]]},
        {'code': 'DPB4104', 'name': 'Droit Public Économique', 'niveaux': [niveaux_master["Droit Public_M1"]]},
        {'code': 'DPB4105', 'name': 'Droit de l\'Urbanisme', 'niveaux': [niveaux_master["Droit Public_M1"]]},
        # M2
        {'code': 'DPB4201', 'name': 'Droit International Public', 'niveaux': [niveaux_master["Droit Public_M2"]]},
        {'code': 'DPB4202', 'name': 'Droit Communautaire', 'niveaux': [niveaux_master["Droit Public_M2"]]},
        {'code': 'DPB4203', 'name': 'Droit de l\'Environnement', 'niveaux': [niveaux_master["Droit Public_M2"]]},
        {'code': 'DPB4204', 'name': 'Droit Fiscal Public', 'niveaux': [niveaux_master["Droit Public_M2"]]},
        {'code': 'TDP4205', 'name': 'Mémoire Droit Public', 'niveaux': [niveaux_master["Droit Public_M2"]]},
    ]

    # ── UEs Master Droit Privé ───────────────────────────────────────────────────
    ues_prive = [
        # M1
        {'code': 'DPR5101', 'name': 'Droit Civil Approfondi', 'niveaux': [niveaux_master["Droit Privé_M1"]]},
        {'code': 'DPR5102', 'name': 'Droit des Contrats Spéciaux', 'niveaux': [niveaux_master["Droit Privé_M1"]]},
        {'code': 'DPR5103', 'name': 'Droit des Sûretés', 'niveaux': [niveaux_master["Droit Privé_M1"]]},
        {'code': 'DPR5104', 'name': 'Droit de la Famille', 'niveaux': [niveaux_master["Droit Privé_M1"]]},
        {'code': 'DPR5105', 'name': 'Droit des Successions', 'niveaux': [niveaux_master["Droit Privé_M1"]]},
        # M2
        {'code': 'DPR5201', 'name': 'Droit International Privé', 'niveaux': [niveaux_master["Droit Privé_M2"]]},
        {'code': 'DPR5202', 'name': 'Droit des Responsabilités', 'niveaux': [niveaux_master["Droit Privé_M2"]]},
        {'code': 'DPR5203', 'name': 'Droit Immobilier', 'niveaux': [niveaux_master["Droit Privé_M2"]]},
        {'code': 'DPR5204', 'name': 'Droit Pénal des Affaires', 'niveaux': [niveaux_master["Droit Privé_M2"]]},
        {'code': 'TDR5205', 'name': 'Mémoire Droit Privé', 'niveaux': [niveaux_master["Droit Privé_M2"]]},
    ]

    # ── Fusionner toutes les UEs ───────────────────────────────────────────────────
    all_ues = ues_tc + ues_contentieux + ues_affaires + ues_public + ues_prive

    created_ues = []
    for ue_data in all_ues:
        ue, created = UE.objects.get_or_create(
            code=ue_data['code'],
            defaults={
                'name': ue_data['name'],
                'coef': 5.00,  # Coefficient par défaut
            }
        )
        
        # Associer les niveaux
        for niveau in ue_data['niveaux']:
            ue.niveaux.add(niveau)
        
        if created:
            print(f"   ✔ UE : {ue.code} — {ue.name}")
        
        # Créer un ECUE par défaut pour cette UE
        ecue, ecue_created = ECUE.objects.get_or_create(
            ue=ue,
            code=f"{ue.code}01",
            defaults={
                'name': f"{ue.name} - Cours",
                'coef': 5.00,
            }
        )
        
        if ecue_created:
            print(f"   ✔ ECUE : {ecue.code} — {ecue.name}")
        
        created_ues.append(ue)

    print(f"   ✔ Toutes les UEs créées avec leurs ECUEs")
    return created_ues


# =============================================================================
# 👥  3. UTILISATEURS (Admin + Biblio + Étudiants)
# =============================================================================

def seed_utilisateurs():
    from apps.users.models import User
    from apps.users.models.etudiant_models import Etudiant
    from apps.users.models.bibliothecaire_models import Bibliothecaire
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n👥 Création des utilisateurs 2025...")

    # ── Récupérer la structure ─────────────────────────────────────────────────
    filiere_tc = Filiere.objects.get(name="Droit (Tronc Commun)")
    filieres_master = {
        "Droit des Contentieux": Filiere.objects.get(name="Droit des Contentieux"),
        "Droit des Affaires": Filiere.objects.get(name="Droit des Affaires"),
        "Droit Public": Filiere.objects.get(name="Droit Public"),
        "Droit Privé": Filiere.objects.get(name="Droit Privé"),
    }
    filiere_doctorat = Filiere.objects.get(name="Doctorat")
    
    niveaux_tc = {
        'L1': Niveau.objects.get(filiere=filiere_tc, name='L1'),
        'L2': Niveau.objects.get(filiere=filiere_tc, name='L2'),
        'L3': Niveau.objects.get(filiere=filiere_tc, name='L3'),
    }
    
    niveaux_master = {}
    for spec_name, filiere in filieres_master.items():
        niveaux_master[f"{spec_name}_M1"] = Niveau.objects.get(filiere=filiere, name='M1')
        niveaux_master[f"{spec_name}_M2"] = Niveau.objects.get(filiere=filiere, name='M2')
    
    doctorat = Niveau.objects.get(filiere=filiere_doctorat, name="DOCTORAT")

    # ── Administrateur ────────────────────────────────────────────────────────
    admin, created = User.objects.get_or_create(
        email='admin@universite-ci.edu',
        defaults={
            'first_name': 'Kouamé',
            'last_name':  'BROU',
            'phone':      '+2250701000001',
            'user_type':  User.UserType.ADMINISTRATEUR,
            'is_staff':   True,
            'is_superuser': True,
            'is_active':  True,
            'is_2fa_enabled': True,
            'password':   make_password('Admin@2025!'),
        }
    )
    if created:
        print(f"   ✔ Admin : {admin.email}")

    # ── Bibliothécaires ───────────────────────────────────────────────────────
    biblios_data = [
        {
            'email':      'biblio.kone@universite-ci.edu',
            'first_name': 'Mariam',
            'last_name':  'KONÉ',
            'phone':      '+2250701000002',
            'badge':      'BIB-2025-001',
        },
        {
            'email':      'biblio.diallo@universite-ci.edu',
            'first_name': 'Seydou',
            'last_name':  'DIALLO',
            'phone':      '+2250701000003',
            'badge':      'BIB-2025-002',
        },
    ]

    for bd in biblios_data:
        user, created = User.objects.get_or_create(
            email=bd['email'],
            defaults={
                'first_name':     bd['first_name'],
                'last_name':      bd['last_name'],
                'phone':          bd['phone'],
                'user_type':      User.UserType.BIBLIOTHECAIRE,
                'is_staff':       True,
                'is_active':      True,
                'is_2fa_enabled': True,
                'password':       make_password('Biblio@2025!'),
            }
        )
        Bibliothecaire.objects.get_or_create(
            user=user,
            defaults={
                'badge_number':          bd['badge'],
                'date_prise_poste':      datetime(2025, 1, 6).date(),
                'peut_gerer_documents':  True,
                'peut_gerer_utilisateurs': True,
            }
        )
        if created:
            print(f"   ✔ Biblio : {user.email}")

    # ── Étudiants Licence (Tronc Commun) ─────────────────────────────────────────
    etudiants_licence = {
        'L1': [
            {'email': 'etu.l1.kone@etud-ci.edu',   'first_name': 'Yao',   'last_name': 'KONÉ',   'phone': '+2250701003001'},
            {'email': 'etu.l1.brou@etud-ci.edu',    'first_name': 'Aminata',  'last_name': 'BROU',    'phone': '+2250701003002'},
            {'email': 'etu.l1.toure@etud-ci.edu',    'first_name': 'Moussa',    'last_name': 'TOURÉ',    'phone': '+2250701003003'},
        ],
        'L2': [
            {'email': 'etu.l2.sangare@etud-ci.edu', 'first_name': 'Fatou',    'last_name': 'SANGARÉ', 'phone': '+2250701004001'},
            {'email': 'etu.l2.ouedraogo@etud-ci.edu','first_name': 'Kouakou',   'last_name': 'OUÉDRAOGO', 'phone': '+2250701004002'},
            {'email': 'etu.l2.kone@etud-ci.edu',     'first_name': 'Adama',     'last_name': 'KONÉ',     'phone': '+2250701004003'},
        ],
        'L3': [
            {'email': 'etu.l3.coulibaly@etud-ci.edu','first_name': 'Brahima',   'last_name': 'COULIBALY', 'phone': '+2250701005001'},
            {'email': 'etu.l3.diarra@etud-ci.edu',   'first_name': 'Mariam',    'last_name': 'DIARRA',   'phone': '+2250701005002'},
            {'email': 'etu.l3.bamba@etud-ci.edu',    'first_name': 'Seydou',    'last_name': 'BAMBA',    'phone': '+2250701005003'},
        ],
    }

    # ── Étudiants Master (Spécialisés) ────────────────────────────────────────────
    etudiants_master = {
        "Droit des Contentieux_M1": [
            {'email': 'etu.dc.m1.kouassi@etud-ci.edu',   'first_name': 'Adjoua',   'last_name': 'KOUASSI',   'phone': '+2250701001001'},
            {'email': 'etu.dc.m1.traore@etud-ci.edu',    'first_name': 'Ibrahim',  'last_name': 'TRAORÉ',    'phone': '+2250701001002'},
        ],
        "Droit des Contentieux_M2": [
            {'email': 'etu.dc.m2.ouattara@etud-ci.edu',  'first_name': 'Salimata', 'last_name': 'OUATTARA',  'phone': '+2250701002001'},
            {'email': 'etu.dc.m2.koffi@etud-ci.edu',     'first_name': 'Jean-Marc','last_name': 'KOFFI',     'phone': '+2250701002002'},
        ],
        "Droit des Affaires_M1": [
            {'email': 'etu.da.m1.yao@etud-ci.edu',       'first_name': 'Brice',    'last_name': 'YAO',       'phone': '+2250701006001'},
            {'email': 'etu.da.m1.coulibaly@etud-ci.edu', 'first_name': 'Fatou',    'last_name': 'COULIBALY', 'phone': '+2250701006002'},
        ],
        "Droit des Affaires_M2": [
            {'email': 'etu.da.m2.gbagbo@etud-ci.edu',    'first_name': 'Olivia',   'last_name': 'GBAGBO',    'phone': '+2250701007001'},
            {'email': 'etu.da.m2.n_goran@etud-ci.edu',   'first_name': 'Rachel',   'last_name': "N'GORAN",   'phone': '+2250701007002'},
        ],
        "Droit Public_M1": [
            {'email': 'etu.dp.m1.kone@etud-ci.edu',      'first_name': 'Kouamé',   'last_name': 'KONÉ',      'phone': '+2250701008001'},
            {'email': 'etu.dp.m1.bamba@etud-ci.edu',     'first_name': 'Moussa',   'last_name': 'BAMBA',     'phone': '+2250701008002'},
        ],
        "Droit Public_M2": [
            {'email': 'etu.dp.m2.ahui@etud-ci.edu',      'first_name': 'Prisca',   'last_name': 'AHUI',      'phone': '+2250701009001'},
            {'email': 'etu.dp.m2.diallo@etud-ci.edu',    'first_name': 'Seydou',   'last_name': 'DIALLO',    'phone': '+2250701009002'},
        ],
        "Droit Privé_M1": [
            {'email': 'etu.dpr.m1.toure@etud-ci.edu',    'first_name': 'Aminata',  'last_name': 'TOURÉ',    'phone': '+2250701010001'},
            {'email': 'etu.dpr.m1.sangare@etud-ci.edu',  'first_name': 'Brahima',  'last_name': 'SANGARÉ',  'phone': '+2250701010002'},
        ],
        "Droit Privé_M2": [
            {'email': 'etu.dpr.m2.ouedraogo@etud-ci.edu','first_name': 'Kouakou',   'last_name': 'OUÉDRAOGO', 'phone': '+2250701011001'},
            {'email': 'etu.dpr.m2.diarra@etud-ci.edu',   'first_name': 'Mariam',    'last_name': 'DIARRA',   'phone': '+2250701011002'},
        ],
    }

    # ── Doctorants ─────────────────────────────────────────────────────────────
    doctorants = [
        {'email': 'doc.these1@doctorant-ci.edu', 'first_name': 'Jean', 'last_name': 'KOUADJA', 'phone': '+2250702000001'},
        {'email': 'doc.these2@doctorant-ci.edu', 'first_name': 'Marie', 'last_name': 'TOURE', 'phone': '+2250702000002'},
        {'email': 'doc.these3@doctorant-ci.edu', 'first_name': 'Paul', 'last_name': 'SANGARE', 'phone': '+2250702000003'},
    ]

    activation_base = timezone.now() - timedelta(days=10)  # activés il y a 10 jours

    # ── Création étudiants Licence ───────────────────────────────────────────────
    for niveau_name, etudiants_list in etudiants_licence.items():
        niveau = niveaux_tc[niveau_name]
        for ed in etudiants_list:
            user, created = User.objects.get_or_create(
                email=ed['email'],
                defaults={
                    'first_name': ed['first_name'],
                    'last_name':  ed['last_name'],
                    'phone':      ed['phone'],
                    'user_type':  User.UserType.ETUDIANT,
                    'is_active':  True,
                    'password':   make_password('Etudiant@2025!'),
                }
            )
            Etudiant.objects.get_or_create(
                user=user,
                defaults={
                    'filiere':           filiere_tc,
                    'niveau':            niveau,
                    'annee_inscription': 2025,
                    'compte_active_le':  activation_base,
                    'compte_expire_le':  activation_base + timedelta(days=30),
                    'nb_reactivations':  0,
                }
            )
            if created:
                print(f"   ✔ Étudiant {niveau_name} : {user.get_full_name()} ({user.matricule})")

    # ── Création étudiants Master ─────────────────────────────────────────────────
    for niveau_key, etudiants_list in etudiants_master.items():
        niveau = niveaux_master[niveau_key]
        specialite = niveau_key.replace('_M1', '').replace('_M2', '')
        filiere = filieres_master[specialite]
        
        for ed in etudiants_list:
            user, created = User.objects.get_or_create(
                email=ed['email'],
                defaults={
                    'first_name': ed['first_name'],
                    'last_name':  ed['last_name'],
                    'phone':      ed['phone'],
                    'user_type':  User.UserType.ETUDIANT,
                    'is_active':  True,
                    'password':   make_password('Etudiant@2025!'),
                }
            )
            Etudiant.objects.get_or_create(
                user=user,
                defaults={
                    'filiere':           filiere,
                    'niveau':            niveau,
                    'annee_inscription': 2025,
                    'compte_active_le':  activation_base,
                    'compte_expire_le':  activation_base + timedelta(days=30),
                    'nb_reactivations':  0,
                }
            )
            if created:
                print(f"   ✔ Étudiant {specialite} : {user.get_full_name()} ({user.matricule})")

    # ── Création Doctorants ───────────────────────────────────────────────────────
    for dd in doctorants:
        user, created = User.objects.get_or_create(
            email=dd['email'],
            defaults={
                'first_name': dd['first_name'],
                'last_name':  dd['last_name'],
                'phone':      dd['phone'],
                'user_type':  User.UserType.ETUDIANT,
                'is_active':  True,
                'password':   make_password('Doctorant@2025!'),
            }
        )
        Etudiant.objects.get_or_create(
            user=user,
            defaults={
                'filiere':           filiere_doctorat,
                'niveau':            doctorat,
                'annee_inscription': 2025,
                'compte_active_le':  activation_base,
                'compte_expire_le':  activation_base + timedelta(days=365),  # 1 an pour doctorants
                'nb_reactivations':  0,
            }
        )
        if created:
            print(f"   ✔ Doctorant : {user.get_full_name()} ({user.matricule})")

    print("   ✔ Tous les utilisateurs créés avec succès")


# =============================================================================
# 📄  4. DOCUMENTS (Cours, Examens, Mémoires, Thèses)
# =============================================================================

def seed_documents():
    from apps.documents.models import Document
    from apps.ue.models import UE, ECUE
    from apps.users.models import User
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n📄 Création des documents 2025...")

    # ── Récupérer la structure ─────────────────────────────────────────────────
    filiere_tc = Filiere.objects.get(name="Droit (Tronc Commun)")
    filieres_master = {
        "Droit des Contentieux": Filiere.objects.get(name="Droit des Contentieux"),
        "Droit des Affaires": Filiere.objects.get(name="Droit des Affaires"),
        "Droit Public": Filiere.objects.get(name="Droit Public"),
        "Droit Privé": Filiere.objects.get(name="Droit Privé"),
    }
    filiere_doctorat = Filiere.objects.get(name="Doctorat")
    
    niveaux_tc = {
        'L1': Niveau.objects.get(filiere=filiere_tc, name='L1'),
        'L2': Niveau.objects.get(filiere=filiere_tc, name='L2'),
        'L3': Niveau.objects.get(filiere=filiere_tc, name='L3'),
    }
    
    niveaux_master = {}
    for spec_name, filiere in filieres_master.items():
        niveaux_master[f"{spec_name}_M1"] = Niveau.objects.get(filiere=filiere, name='M1')
        niveaux_master[f"{spec_name}_M2"] = Niveau.objects.get(filiere=filiere, name='M2')
    
    doctorat = Niveau.objects.get(filiere=filiere_doctorat, name="DOCTORAT")
    
    biblio = User.objects.get(email='biblio.kone@universite-ci.edu')
    admin = User.objects.get(email='admin@universite-ci.edu')

    # ── Documents Licence (Tronc Commun) ───────────────────────────────────────────
    docs_licence = [
        # L1
        {'title': 'Cours — Introduction au droit constitutionnel', 'type': 'COURS', 'ue_code': 'DGL101', 'niveau': niveaux_tc['L1'], 'encadreur': 'Pr. KONAN Yapo', 'jours_avant': 120},
        {'title': 'Cours — Droit civil des personnes physiques', 'type': 'COURS', 'ue_code': 'DGL102', 'niveau': niveaux_tc['L1'], 'encadreur': 'Dr. TOURE Awa', 'jours_avant': 115},
        {'title': 'Examen L1 — Droit constitutionnel général', 'type': 'EXAMEN', 'ue_code': 'DGL101', 'niveau': niveaux_tc['L1'], 'encadreur': 'Pr. KONAN Yapo', 'jours_avant': 90},
        
        # L2
        {'title': 'Cours — Droit des obligations', 'type': 'COURS', 'ue_code': 'DGL106', 'niveau': niveaux_tc['L2'], 'encadreur': 'Pr. Bamba Kouamé', 'jours_avant': 110},
        {'title': 'Cours — Droit pénal général', 'type': 'COURS', 'ue_code': 'DGL103', 'niveau': niveaux_tc['L2'], 'encadreur': 'Dr. SANGARÉ Adama', 'jours_avant': 105},
        {'title': 'Examen L2 — Droit des obligations', 'type': 'EXAMEN', 'ue_code': 'DGL106', 'niveau': niveaux_tc['L2'], 'encadreur': 'Pr. Bamba Kouamé', 'jours_avant': 80},
        
        # L3
        {'title': 'Cours — Droit administratif général', 'type': 'COURS', 'ue_code': 'DGL108', 'niveau': niveaux_tc['L3'], 'encadreur': 'Pr. OUATTARA Bakary', 'jours_avant': 100},
        {'title': 'Cours — Histoire du droit', 'type': 'COURS', 'ue_code': 'DGL105', 'niveau': niveaux_tc['L3'], 'encadreur': 'Dr. KONATE Fatou', 'jours_avant': 95},
        {'title': 'Examen L3 — Droit administratif', 'type': 'EXAMEN', 'ue_code': 'DGL108', 'niveau': niveaux_tc['L3'], 'encadreur': 'Pr. OUATTARA Bakary', 'jours_avant': 70},
    ]

    # ── Documents Master Droit des Contentieux ───────────────────────────────────────
    docs_contentieux = [
        # M1
        {'title': 'Cours — Le contrôle par voie d\'action', 'type': 'COURS', 'ue_code': 'COC2102', 'niveau': niveaux_master["Droit des Contentieux_M1"], 'encadreur': 'Pr. ASSI Jean-Baptiste', 'jours_avant': 90},
        {'title': 'Cours — La responsabilité administrative', 'type': 'COURS', 'ue_code': 'COA2101', 'niveau': niveaux_master["Droit des Contentieux_M1"], 'encadreur': 'Dr. KONAN Adjoua Marie', 'jours_avant': 85},
        {'title': 'Examen M1 — Contentieux constitutionnel', 'type': 'EXAMEN', 'ue_code': 'COC2102', 'niveau': niveaux_master["Droit des Contentieux_M1"], 'encadreur': 'Pr. ASSI Jean-Baptiste', 'jours_avant': 60},
        
        # M2
        {'title': 'Cours — Contentieux électoral', 'type': 'COURS', 'ue_code': 'CPB2301', 'niveau': niveaux_master["Droit des Contentieux_M2"], 'encadreur': 'Pr. ASSI Jean-Baptiste', 'jours_avant': 45},
        {'title': 'Cours — Arbitrage régional et national', 'type': 'COURS', 'ue_code': 'DER2303', 'niveau': niveaux_master["Droit des Contentieux_M2"], 'encadreur': 'Pr. KOFFI Edmond', 'jours_avant': 40},
        {'title': 'Mémoire — L\'arbitrage OHADA face aux juridictions étatiques', 'type': 'MEMOIRE', 'ue_code': 'TCC2307', 'niveau': niveaux_master["Droit des Contentieux_M2"], 'auteur': 'OUATTARA Salimata', 'encadreur': 'Pr. KOFFI Edmond', 'jours_avant': 30},
        {'title': 'Mémoire — Le recours en annulation devant le Conseil d\'État', 'type': 'MEMOIRE', 'ue_code': 'TCC2307', 'niveau': niveaux_master["Droit des Contentieux_M2"], 'auteur': 'KOFFI Jean-Marc', 'encadreur': 'Dr. KONAN Adjoua Marie', 'jours_avant': 25},
    ]

    # ── Documents Master Droit des Affaires ───────────────────────────────────────────
    docs_affaires = [
        # M1
        {'title': 'Cours — Droit des sociétés commerciales', 'type': 'COURS', 'ue_code': 'DAC3101', 'niveau': niveaux_master["Droit des Affaires_M1"], 'encadreur': 'Pr. YAO Kouamé', 'jours_avant': 88},
        {'title': 'Cours — Droit bancaire et financier', 'type': 'COURS', 'ue_code': 'DAC3103', 'niveau': niveaux_master["Droit des Affaires_M1"], 'encadreur': 'Dr. KONE Mariam', 'jours_avant': 83},
        {'title': 'Examen M1 — Droit des sociétés', 'type': 'EXAMEN', 'ue_code': 'DAC3101', 'niveau': niveaux_master["Droit des Affaires_M1"], 'encadreur': 'Pr. YAO Kouamé', 'jours_avant': 58},
        
        # M2
        {'title': 'Cours — Propriété intellectuelle', 'type': 'COURS', 'ue_code': 'DAC3203', 'niveau': niveaux_master["Droit des Affaires_M2"], 'encadreur': 'Pr. DIALLO Seydou', 'jours_avant': 43},
        {'title': 'Mémoire — La protection des marques en Afrique', 'type': 'MEMOIRE', 'ue_code': 'TDA3205', 'niveau': niveaux_master["Droit des Affaires_M2"], 'auteur': 'GBAGBO Olivia', 'encadreur': 'Pr. DIALLO Seydou', 'jours_avant': 28},
    ]

    # ── Documents Master Droit Public ─────────────────────────────────────────────────
    docs_public = [
        # M1
        {'title': 'Cours — Droit administratif approfondi', 'type': 'COURS', 'ue_code': 'DPB4101', 'niveau': niveaux_master["Droit Public_M1"], 'encadreur': 'Pr. TOURE Issiaka', 'jours_avant': 86},
        {'title': 'Cours — Droit des libertés fondamentales', 'type': 'COURS', 'ue_code': 'DPB4103', 'niveau': niveaux_master["Droit Public_M1"], 'encadreur': 'Dr. BONI Clarisse', 'jours_avant': 81},
        {'title': 'Examen M1 — Droit administratif', 'type': 'EXAMEN', 'ue_code': 'DPB4101', 'niveau': niveaux_master["Droit Public_M1"], 'encadreur': 'Pr. TOURE Issiaka', 'jours_avant': 56},
        
        # M2
        {'title': 'Cours — Droit international public', 'type': 'COURS', 'ue_code': 'DPB4201', 'niveau': niveaux_master["Droit Public_M2"], 'encadreur': 'Pr. KOFFI Edmond', 'jours_avant': 41},
        {'title': 'Mémoire — Le contentieux électoral en Afrique de l\'Ouest', 'type': 'MEMOIRE', 'ue_code': 'TDP4205', 'niveau': niveaux_master["Droit Public_M2"], 'auteur': 'AHUI Prisca', 'encadreur': 'Pr. TOURE Issiaka', 'jours_avant': 26},
    ]

    # ── Documents Master Droit Privé ─────────────────────────────────────────────────
    docs_prive = [
        # M1
        {'title': 'Cours — Droit civil approfondi', 'type': 'COURS', 'ue_code': 'DPR5101', 'niveau': niveaux_master["Droit Privé_M1"], 'encadreur': 'Pr. COULIBALY Nathalie', 'jours_avant': 84},
        {'title': 'Cours — Droit des sûretés', 'type': 'COURS', 'ue_code': 'DPR5103', 'niveau': niveaux_master["Droit Privé_M1"], 'encadreur': 'Dr. GNANGUI Pamela', 'jours_avant': 79},
        {'title': 'Examen M1 — Droit civil', 'type': 'EXAMEN', 'ue_code': 'DPR5101', 'niveau': niveaux_master["Droit Privé_M1"], 'encadreur': 'Pr. COULIBALY Nathalie', 'jours_avant': 54},
        
        # M2
        {'title': 'Cours — Droit international privé', 'type': 'COURS', 'ue_code': 'DPR5201', 'niveau': niveaux_master["Droit Privé_M2"], 'encadreur': 'Pr. CAMARA Bintou', 'jours_avant': 39},
        {'title': 'Mémoire — La preuve électronique dans le contentieux civil', 'type': 'MEMOIRE', 'ue_code': 'TDR5205', 'niveau': niveaux_master["Droit Privé_M2"], 'auteur': 'N\'GORAN Rachel', 'encadreur': 'Dr. GNANGUI Pamela', 'jours_avant': 24},
    ]

    # ── Thèses Doctorat ─────────────────────────────────────────────────────────────
    docs_theses = [
        {'title': 'Thèse — L\'effectivité des décisions de la COUR CEDEAO des droits de l\'homme', 'type': 'THESE', 'niveau': doctorat, 'filiere': filiere_doctorat, 'auteur': 'KOUADJA Jean', 'encadreur': 'Pr. ASSI Jean-Baptiste', 'jours_avant': 20},
        {'title': 'Thèse — Le contentieux électoral en Afrique de l\'Ouest : étude comparée', 'type': 'THESE', 'niveau': doctorat, 'filiere': filiere_doctorat, 'auteur': 'TOURE Marie', 'encadreur': 'Pr. TOURE Issiaka', 'jours_avant': 18},
        {'title': 'Thèse — L\'arbitrage international en matière d\'investissement', 'type': 'THESE', 'niveau': doctorat, 'filiere': filiere_doctorat, 'auteur': 'SANGARE Paul', 'encadreur': 'Pr. KOFFI Edmond', 'jours_avant': 15},
    ]

    # ── Fusionner tous les documents ─────────────────────────────────────────────────
    all_docs = docs_licence + docs_contentieux + docs_affaires + docs_public + docs_prive + docs_theses

    created_docs = []
    for dd in all_docs:
        # Récupérer l'UE si spécifiée
        ue = None
        ecue = None
        if 'ue_code' in dd:
            try:
                ue = UE.objects.get(code=dd['ue_code'])
                # Récupérer le premier ECUE de cette UE
                ecue = ue.ecues.first()
                if not ecue:
                    print(f"   ⚠️ Aucun ECUE trouvé pour l'UE: {dd['ue_code']}")
                    continue
            except UE.DoesNotExist:
                print(f"   ⚠️ UE non trouvée: {dd['ue_code']}")
                continue

        date_c = timezone.now() - timedelta(days=dd['jours_avant'])
        
        doc, created = Document.objects.get_or_create(
            title=dd['title'],
            defaults={
                'type': dd['type'],
                'filiere': dd.get('filiere', ue.niveaux.first().filiere if ue else None),
                'niveau': dd['niveau'],
                'ue': ecue,  # Utiliser ECUE au lieu de UE
                'auteur': dd.get('auteur', ''),
                'encadreur': dd.get('encadreur', ''),
                'file_path': f"documents/{dd['type'].lower()}/{dd['title'][:30].replace(' ','_')}.pdf",
                'description': f"Document de {dd['type'].lower()} — {ue.code if ue else 'Doctorat'} — 2025",
                'ajoute_par': dd.get('ajoute_par', biblio),
                'created_at': date_c,
            }
        )
        created_docs.append(doc)
        if created:
            print(f"   ✔ [{dd['type']}] {dd['title'][:60]}...")

    print(f"   ✔ {len(created_docs)} documents créés au total")
    return created_docs


# =============================================================================
# 👁️  5. CONSULTATIONS, FAVORIS & HISTORIQUE ACTIONS
# =============================================================================

def seed_consultations_favoris():
    from apps.users.models import User
    from apps.users.models.etudiant_models import Etudiant
    from apps.documents.models import Document
    from apps.consultations.models import Consultation
    from apps.documents.models import Favori
    from apps.history.models import HistoriqueActionService

    print("\n👁️  Création des consultations, favoris & logs 2025...")

    # Récupérer tous les étudiants
    etudiants = list(Etudiant.objects.select_related('user').all())
    # Récupérer tous les documents
    tous_docs  = list(Document.objects.all())
    biblio     = User.objects.get(email='biblio.kone@universite-ci.edu')
    admin_user = User.objects.get(email='admin@universite-ci.edu')

    if not etudiants or not tous_docs:
        print("   ⚠️  Pas d'étudiants ou de documents trouvés, skip.")
        return

    # ── Interactions par étudiant ─────────────────────────────────────────────
    interactions = [
        # (email_etudiant, [(titre_partiel_doc, type_action, duree_sec, en_favori)])
        ('etu.dc.m1.kouassi@etud-ci.edu', [
            ('Cours — Le contrôle par voie', 'VUE', 420, True),
            ('Cours — La responsabilité', 'VUE', 360, True),
            ('Examen M1 — Contentieux constitutionnel', 'VUE', 180, True),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 600, False),
        ]),
        ('etu.dc.m1.traore@etud-ci.edu', [
            ('Cours — La procédure du contentieux civil', 'VUE', 500, True),
            ('Cours — Contentieux pénal', 'VUE', 310, False),
            ('Examen M1 — Contentieux administratif', 'VUE', 240, True),
            ('Thèse — Le contentieux électoral', 'VUE', 720, True),
        ]),
        ('etu.da.m1.yao@etud-ci.edu', [
            ('Cours — Voies d\'exécution', 'VUE', 280, False),
            ('Cours — Arbitrage régional', 'VUE', 450, True),
            ('Examen M1 — Droit de l\'arbitrage', 'VUE', 200, True),
            ('Mémoire — Le recours en annulation', 'VUE', 530, False),
        ]),
        ('etu.dpr.m1.toure@etud-ci.edu', [
            ('Cours — Les grands principes du contentieux international', 'VUE', 390, True),
            ('Cours — La classification du formalisme', 'VUE', 260, True),
            ('Examen M1 — Contentieux international pénal', 'VUE', 300, True),
            ('Thèse — L\'effectivité des décisions', 'VUE', 810, True),
        ]),
        ('etu.da.m2.gbagbo@etud-ci.edu', [
            ('Cours — Contentieux de la Cour Internationale', 'VUE', 340, False),
            ('Cours — Le contentieux des sociétés', 'VUE', 290, True),
            ('Mémoire — La preuve électronique', 'VUE', 480, True),
            ('Examen M1 — Contentieux international public', 'VUE', 150, False),
        ]),
        # M2
        ('etu.dc.m2.ouattara@etud-ci.edu', [
            ('Cours — Contentieux électoral', 'VUE', 520, True),
            ('Cours — Arbitrage régional', 'VUE', 410, True),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 900, True),
            ('Thèse — Le contentieux électoral', 'VUE', 660, True),
        ]),
        ('etu.dc.m2.koffi@etud-ci.edu', [
            ('Cours — Les grands principes du contentieux international', 'VUE', 430, True),
            ('Examen M1 — Contentieux international pénal', 'VUE', 370, True),
            ('Mémoire — Le recours en annulation', 'VUE', 580, False),
            ('Thèse — L\'effectivité des décisions', 'VUE', 750, False),
        ]),
        ('etu.da.m2.n_goran@etud-ci.edu', [
            ('Cours — La classification du formalisme', 'VUE', 300, True),
            ('Mémoire — La preuve électronique', 'VUE', 680, True),
            ('Examen M1 — Droit de l\'arbitrage', 'VUE', 220, True),
            ('Cours — Arbitrage régional', 'VUE', 490, False),
        ]),
        ('etu.dp.m2.ahui@etud-ci.edu', [
            ('Thèse — Le contentieux électoral', 'VUE', 840, True),
            ('Cours — Contentieux électoral', 'VUE', 360, True),
            ('Examen M1 — Contentieux constitutionnel', 'VUE', 190, False),
            ('Cours — Le contrôle par voie', 'VUE', 440, False),
        ]),
        ('etu.dp.m2.diallo@etud-ci.edu', [
            ('Thèse — L\'effectivité des décisions', 'VUE', 920, True),
            ('Cours — Voies d\'exécution', 'VUE', 260, False),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 510, True),
            ('Examen M1 — Contentieux administratif', 'VUE', 280, True),
        ]),
    ]

    # ── Recherches effectuées ─────────────────────────────────────────────────
    recherches = [
        ('etu.dc.m1.kouassi@etud-ci.edu',  'arbitrage OHADA',          -20),
        ('etu.dc.m1.traore@etud-ci.edu',   'contentieux civil',         -18),
        ('etu.da.m1.yao@etud-ci.edu',      'procédures d\'urgence',     -15),
        ('etu.dpr.m1.toure@etud-ci.edu', 'preuve électronique',        -12),
        ('etu.da.m2.gbagbo@etud-ci.edu',   'contentieux international',  -10),
        ('etu.dc.m2.ouattara@etud-ci.edu', 'mémoire arbitrage',          -8),
        ('etu.dc.m2.koffi@etud-ci.edu',    'examen droit pénal',         -6),
        ('etu.da.m2.n_goran@etud-ci.edu',  'rédaction actes juridiques', -5),
        ('etu.dp.m2.ahui@etud-ci.edu',     'contentieux électoral',      -4),
        ('etu.dp.m2.diallo@etud-ci.edu',   'CEDEAO droits homme',        -3),
    ]

    nb_consultations = 0
    nb_favoris       = 0
    nb_recherches    = 0

    for email_etu, actions in interactions:
        try:
            user = User.objects.get(email=email_etu)
            etu  = Etudiant.objects.get(user=user)
        except (User.DoesNotExist, Etudiant.DoesNotExist):
            continue

        for i, (titre_partiel, type_action, duree, en_favori) in enumerate(actions):
            # Trouver le document correspondant
            doc = next((d for d in tous_docs if titre_partiel.lower() in d.title.lower()), None)
            if not doc:
                continue

            # Créer la consultation
            debut = timezone.now() - timedelta(days=15 - i, hours=i * 2)
            fin   = debut + timedelta(seconds=duree)

            _, created = Consultation.objects.get_or_create(
                user=user,
                document=doc,
                debut_consultation=debut,
                defaults={
                    'type_consultation': type_action,
                    'fin_consultation':  fin,
                    'duree_secondes':    duree,
                    'ip_address':        f'192.168.1.{10 + i}',
                    'user_agent':        'Mozilla/5.0 (Windows NT 10.0) Chrome/120.0',
                }
            )
            if created:
                nb_consultations += 1

            # Créer le favori si demandé
            if en_favori:
                _, fav_created = Favori.objects.get_or_create(
                    etudiant=etu,
                    document=doc
                )
                if fav_created:
                    nb_favoris += 1

    # ── Recherches ────────────────────────────────────────────────────────────
    for email_etu, query, jours in recherches:
        try:
            user = User.objects.get(email=email_etu)
        except User.DoesNotExist:
            continue

        _, created = Consultation.objects.get_or_create(
            user=user,
            type_consultation='RECHERCHE',
            recherche_query=query,
            defaults={
                'debut_consultation': timezone.now() + timedelta(days=jours),
                'ip_address':         '192.168.1.50',
                'user_agent':         'Mozilla/5.0 (Android) Mobile',
            }
        )
        if created:
            nb_recherches += 1

    print(f"   ✔ {nb_consultations} consultations créées")
    print(f"   ✔ {nb_favoris} favoris créés")
    print(f"   ✔ {nb_recherches} recherches créées")

    # ── Historique actions MongoDB ────────────────────────────────────────────
    _seed_historique_actions(admin_user, biblio)


def _seed_historique_actions(admin_user, biblio):
    """Insère des logs réalistes dans MongoDB."""
    from apps.users.models import User
    from apps.documents.models import Document
    from apps.history.models import HistoriqueActionService as HAS

    print("\n📋 Insertion logs MongoDB (HistoriqueAction)...")

    tous_etudiants = list(User.objects.filter(user_type='ETUDIANT'))
    tous_docs      = list(Document.objects.all()[:5])

    nb_logs = 0

    # Connexions des étudiants (7 derniers jours)
    for i, user in enumerate(tous_etudiants):
        result = HAS.log_connexion(
            user=user,
            statut='succes',
            ip=f'192.168.1.{20 + i}',
            ua='Mozilla/5.0 Chrome/120.0'
        )
        if result:
            nb_logs += 1

    # 3 tentatives de connexion échouées
    for i, user in enumerate(tous_etudiants[:3]):
        HAS.log_connexion(user=user, statut='echec', ip='10.0.0.99')
        nb_logs += 1

    # Tentatives OTP échouées
    for user in tous_etudiants[:2]:
        HAS.log(
            action=HAS.ACTIONS.OTP_ECHEC,
            user=user,
            statut='echec',
            ip_address='10.0.0.50',
            ua='Mozilla/5.0 (iPhone) Safari/605.1.15'
        )
        nb_logs += 1

    # Ajouts de documents par bibliothécaire
    for i, doc in enumerate(tous_docs):
        HAS.log(
            action=HAS.ACTIONS.DOCUMENT_AJOUTE,
            user=biblio,
            statut='succes',
            ip_address='192.168.1.10',
            details={
                'document_id': str(doc.id),
                'document_title': doc.title,
                'document_type': doc.type
            }
        )
        nb_logs += 1

    print(f"   ✔ {nb_logs} logs d'actions insérés dans MongoDB")


# =============================================================================
# 🚀 EXECUTION
# =============================================================================

if __name__ == "__main__":
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    seed_all()
