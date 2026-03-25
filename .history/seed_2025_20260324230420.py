"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — fixtures/seed_2025.py
 Données de test 2025 — Master Droit des Contentieux
 
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

    filiere, _ = Filiere.objects.get_or_create(
        name="Droit des Contentieux",
        defaults={'id': uuid.UUID('aaaaaaaa-0001-0001-0001-000000000001')}
    )

    niveaux_data = ['L1', 'L2', 'L3', 'M1', 'M2']
    niveaux = {}
    for n in niveaux_data:
        obj, _ = Niveau.objects.get_or_create(
            filiere=filiere, name=n
        )
        niveaux[n] = obj

    print(f"   ✔ Filière : {filiere.name}")
    print(f"   ✔ Niveaux : {', '.join(niveaux_data)}")
    return filiere, niveaux


# =============================================================================
# 📖  2. UEs & ECUEs (issues des images)
# =============================================================================

def seed_ues_ecues():
    from apps.documents.models import UE
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n📖 Création UEs & ECUEs Master Droit des Contentieux 2025...")

    filiere  = Filiere.objects.get(name="Droit des Contentieux")
    m1       = Niveau.objects.get(filiere=filiere, name='M1')
    m2       = Niveau.objects.get(filiere=filiere, name='M2')

    # ── Semestre 1 (M1) ───────────────────────────────────────────────────────
    ues_s1 = [
        {'code': 'COC2102', 'name': 'Contentieux constitutionnel',          'coef': 2.00},
        {'code': 'COA2101', 'name': 'Contentieux administratif',            'coef': 2.00},
        {'code': 'CCI2103', 'name': 'Contentieux civil',                    'coef': 2.00},
        {'code': 'COF2104', 'name': 'Contentieux fiscal',                   'coef': 1.50},
        {'code': 'CPN2105', 'name': 'Contentieux pénal',                    'coef': 1.50},
    ]

    # ── Semestre 2 (M1) ───────────────────────────────────────────────────────
    ues_s2 = [
        {'code': 'CIP2201', 'name': 'Contentieux international public',     'coef': 2.00},
        {'code': 'CIE2202', 'name': 'Contentieux international économique', 'coef': 2.00},
        {'code': 'CCM2203', 'name': 'Contentieux commercial',               'coef': 1.50},
        {'code': 'VEX2204', 'name': "Voies d'exécution et procédure d'urgence", 'coef': 1.50},
        {'code': 'DPR2206', 'name': 'Droit de la preuve',                   'coef': 1.00},
    ]

    # ── Semestre 3 (M2) ───────────────────────────────────────────────────────
    ues_s3 = [
        {'code': 'CPB2301', 'name': 'Contentieux interne public spécialisé','coef': 2.00},
        {'code': 'CIS2302', 'name': 'Contentieux international spécialisé', 'coef': 2.00},
        {'code': 'DER2303', 'name': "Droit de l'arbitrage",                 'coef': 2.00},
        {'code': 'DIC2304', 'name': 'Contentieux international pénal',      'coef': 2.00},
        {'code': 'RAC2305', 'name': "Rédaction d'actes",                    'coef': 1.50},
        {'code': 'MET2306', 'name': "Méthodologie d'élaboration",           'coef': 1.00},
    ]

    # ── Semestre 4 (M2) ───────────────────────────────────────────────────────
    ues_s4 = [
        {'code': 'TCC2307', 'name': 'Mémoire',                              'coef': 4.00},
    ]

    for ue_data in ues_s1 + ues_s2:
        ue, created = UE.objects.get_or_create(
            code=ue_data['code'],
            defaults={'name': ue_data['name'], 'coef': ue_data['coef']}
        )
        ue.niveaux.add(m1)
        if created:
            print(f"   ✔ UE M1 : {ue.code} — {ue.name}")

    for ue_data in ues_s3 + ues_s4:
        ue, created = UE.objects.get_or_create(
            code=ue_data['code'],
            defaults={'name': ue_data['name'], 'coef': ue_data['coef']}
        )
        ue.niveaux.add(m2)
        if created:
            print(f"   ✔ UE M2 : {ue.code} — {ue.name}")


# =============================================================================
# 👥  3. UTILISATEURS (Admin + Biblio + Étudiants)
# =============================================================================

def seed_utilisateurs():
    from apps.users.models import User
    from apps.etudiant.models import Etudiant
    from apps.bibliothecaire.models import Bibliothecaire
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n👥 Création des utilisateurs 2025...")

    filiere = Filiere.objects.get(name="Droit des Contentieux")
    m1      = Niveau.objects.get(filiere=filiere, name='M1')
    m2      = Niveau.objects.get(filiere=filiere, name='M2')

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

    # ── Étudiants M1 ─────────────────────────────────────────────────────────
    etudiants_m1 = [
        {'email': 'etu.kouassi@etud-ci.edu',   'first_name': 'Adjoua',   'last_name': 'KOUASSI',   'phone': '+2250701001001'},
        {'email': 'etu.traore@etud-ci.edu',    'first_name': 'Ibrahim',  'last_name': 'TRAORÉ',    'phone': '+2250701001002'},
        {'email': 'etu.yao@etud-ci.edu',       'first_name': 'Brice',    'last_name': 'YAO',       'phone': '+2250701001003'},
        {'email': 'etu.coulibaly@etud-ci.edu', 'first_name': 'Fatou',    'last_name': 'COULIBALY', 'phone': '+2250701001004'},
        {'email': 'etu.gbagbo@etud-ci.edu',    'first_name': 'Olivia',   'last_name': 'GBAGBO',    'phone': '+2250701001005'},
    ]

    # ── Étudiants M2 ─────────────────────────────────────────────────────────
    etudiants_m2 = [
        {'email': 'etu.ouattara@etud-ci.edu',  'first_name': 'Salimata', 'last_name': 'OUATTARA',  'phone': '+2250701002001'},
        {'email': 'etu.koffi@etud-ci.edu',     'first_name': 'Jean-Marc','last_name': 'KOFFI',     'phone': '+2250701002002'},
        {'email': 'etu.n_goran@etud-ci.edu',   'first_name': 'Rachel',   'last_name': "N'GORAN",   'phone': '+2250701002003'},
        {'email': 'etu.bamba@etud-ci.edu',     'first_name': 'Moussa',   'last_name': 'BAMBA',     'phone': '+2250701002004'},
        {'email': 'etu.ahui@etud-ci.edu',      'first_name': 'Prisca',   'last_name': 'AHUI',      'phone': '+2250701002005'},
    ]

    activation_base = timezone.now() - timedelta(days=10)  # activés il y a 10 jours

    for ed in etudiants_m1:
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
                'niveau':            m1,
                'annee_inscription': 2025,
                'compte_active_le':  activation_base,
                'compte_expire_le':  activation_base + timedelta(days=30),
                'nb_reactivations':  0,
            }
        )
        if created:
            print(f"   ✔ Étudiant M1 : {user.get_full_name()} ({user.matricule})")

    for ed in etudiants_m2:
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
                'niveau':            m2,
                'annee_inscription': 2025,
                'compte_active_le':  activation_base,
                'compte_expire_le':  activation_base + timedelta(days=30),
                'nb_reactivations':  0,
            }
        )
        if created:
            print(f"   ✔ Étudiant M2 : {user.get_full_name()} ({user.matricule})")


# =============================================================================
# 📄  4. DOCUMENTS (Cours, Examens, Mémoires, Thèses)
# =============================================================================

def seed_documents():
    from apps.documents.models import Document, UE
    from apps.users.models import User
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n📄 Création des documents 2025...")

    filiere  = Filiere.objects.get(name="Droit des Contentieux")
    m1       = Niveau.objects.get(filiere=filiere, name='M1')
    m2       = Niveau.objects.get(filiere=filiere, name='M2')
    biblio   = User.objects.get(email='biblio.kone@universite-ci.edu')
    admin    = User.objects.get(email='admin@universite-ci.edu')

    docs_data = [

        # ── COURS M1 Semestre 1 ───────────────────────────────────────────────
        {
            'title':    'Cours — Le contrôle par voie d\'action',
            'type':     'COURS',
            'ue_code':  'COC2102',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Pr. ASSI Jean-Baptiste',
            'ajoute_par': biblio,
            'jours_avant': 90,
        },
        {
            'title':    'Cours — La responsabilité administrative',
            'type':     'COURS',
            'ue_code':  'COA2101',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Dr. KONAN Adjoua Marie',
            'ajoute_par': biblio,
            'jours_avant': 85,
        },
        {
            'title':    'Cours — La procédure du contentieux civil',
            'type':     'COURS',
            'ue_code':  'CCI2103',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Pr. YAPI Kouamé',
            'ajoute_par': biblio,
            'jours_avant': 80,
        },
        {
            'title':    'Cours — Contentieux pénal national',
            'type':     'COURS',
            'ue_code':  'CPN2105',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Dr. DIOMANDÉ Saliou',
            'ajoute_par': biblio,
            'jours_avant': 75,
        },

        # ── COURS M1 Semestre 2 ───────────────────────────────────────────────
        {
            'title':    'Cours — Contentieux de la Cour Internationale de Justice',
            'type':     'COURS',
            'ue_code':  'CIP2201',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Pr. TOURÉ Issiaka',
            'ajoute_par': biblio,
            'jours_avant': 60,
        },
        {
            'title':    'Cours — Le contentieux des sociétés commerciales',
            'type':     'COURS',
            'ue_code':  'CCM2203',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Dr. BONI Clarisse',
            'ajoute_par': biblio,
            'jours_avant': 55,
        },
        {
            'title':    'Cours — Voies d\'exécution',
            'type':     'COURS',
            'ue_code':  'VEX2204',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Dr. GNANGUI Pamela',
            'ajoute_par': biblio,
            'jours_avant': 50,
        },

        # ── COURS M2 Semestre 3 ───────────────────────────────────────────────
        {
            'title':    'Cours — Contentieux électoral',
            'type':     'COURS',
            'ue_code':  'CPB2301',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Pr. ASSI Jean-Baptiste',
            'ajoute_par': biblio,
            'jours_avant': 45,
        },
        {
            'title':    'Cours — Arbitrage régional et national',
            'type':     'COURS',
            'ue_code':  'DER2303',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Pr. KOFFI Edmond',
            'ajoute_par': biblio,
            'jours_avant': 40,
        },
        {
            'title':    'Cours — Les grands principes du contentieux international pénal',
            'type':     'COURS',
            'ue_code':  'DIC2304',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Dr. COULIBALY Nathalie',
            'ajoute_par': biblio,
            'jours_avant': 38,
        },
        {
            'title':    'Cours — La classification du formalisme écrit et verbal',
            'type':     'COURS',
            'ue_code':  'RAC2305',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Dr. CAMARA Bintou',
            'ajoute_par': biblio,
            'jours_avant': 35,
        },

        # ── EXAMENS ───────────────────────────────────────────────────────────
        {
            'title':    'Examen 2024 — Contentieux constitutionnel (S1)',
            'type':     'EXAMEN',
            'ue_code':  'COC2102',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Pr. ASSI Jean-Baptiste',
            'ajoute_par': admin,
            'jours_avant': 30,
        },
        {
            'title':    'Examen 2024 — Contentieux administratif (S1)',
            'type':     'EXAMEN',
            'ue_code':  'COA2101',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Dr. KONAN Adjoua Marie',
            'ajoute_par': admin,
            'jours_avant': 28,
        },
        {
            'title':    'Examen 2024 — Contentieux international public (S2)',
            'type':     'EXAMEN',
            'ue_code':  'CIP2201',
            'niveau':   m1,
            'auteur':   '',
            'encadreur':'Pr. TOURÉ Issiaka',
            'ajoute_par': admin,
            'jours_avant': 25,
        },
        {
            'title':    'Examen 2024 — Droit de l\'arbitrage (S3)',
            'type':     'EXAMEN',
            'ue_code':  'DER2303',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Pr. KOFFI Edmond',
            'ajoute_par': admin,
            'jours_avant': 20,
        },
        {
            'title':    'Examen 2024 — Contentieux international pénal (S3)',
            'type':     'EXAMEN',
            'ue_code':  'DIC2304',
            'niveau':   m2,
            'auteur':   '',
            'encadreur':'Dr. COULIBALY Nathalie',
            'ajoute_par': admin,
            'jours_avant': 18,
        },

        # ── MÉMOIRES ─────────────────────────────────────────────────────────
        {
            'title':    'Mémoire — L\'arbitrage OHADA face aux juridictions étatiques',
            'type':     'MEMOIRE',
            'ue_code':  'TCC2307',
            'niveau':   m2,
            'auteur':   'OUATTARA Salimata',
            'encadreur':'Pr. KOFFI Edmond',
            'ajoute_par': admin,
            'jours_avant': 15,
        },
        {
            'title':    'Mémoire — Le recours en annulation devant le Conseil d\'État ivoirien',
            'type':     'MEMOIRE',
            'ue_code':  'TCC2307',
            'niveau':   m2,
            'auteur':   'KOFFI Jean-Marc',
            'encadreur':'Dr. KONAN Adjoua Marie',
            'ajoute_par': admin,
            'jours_avant': 12,
        },
        {
            'title':    'Mémoire — La preuve électronique dans le contentieux commercial',
            'type':     'MEMOIRE',
            'ue_code':  'TCC2307',
            'niveau':   m2,
            'auteur':   "N'GORAN Rachel",
            'encadreur':'Dr. BONI Clarisse',
            'ajoute_par': admin,
            'jours_avant': 10,
        },

        # ── THÈSES ────────────────────────────────────────────────────────────
        {
            'title':    'Thèse — Le contentieux électoral en Afrique de l\'Ouest : étude comparée',
            'type':     'THESE',
            'ue_code':  'CPB2301',
            'niveau':   m2,
            'auteur':   'BAMBA Moussa',
            'encadreur':'Pr. ASSI Jean-Baptiste',
            'ajoute_par': admin,
            'jours_avant': 8,
        },
        {
            'title':    'Thèse — L\'effectivité des décisions de la COUR CEDEAO des droits de l\'homme',
            'type':     'THESE',
            'ue_code':  'CIS2302',
            'niveau':   m2,
            'auteur':   'AHUI Prisca',
            'encadreur':'Pr. TOURÉ Issiaka',
            'ajoute_par': admin,
            'jours_avant': 5,
        },
    ]

    created_docs = []
    for dd in docs_data:
        ue      = UE.objects.filter(code=dd['ue_code']).first()
        date_c  = timezone.now() - timedelta(days=dd['jours_avant'])
        doc, c  = Document.objects.get_or_create(
            title=dd['title'],
            defaults={
                'type':        dd['type'],
                'filiere':     filiere,
                'niveau':      dd['niveau'],
                'ue':          ue,
                'auteur':      dd['auteur'],
                'encadreur':   dd['encadreur'],
                'file_path':   f"documents/{dd['type'].lower()}/{dd['title'][:30].replace(' ','_')}.pdf",
                'description': f"Document de {dd['type'].lower()} — {dd['ue_code']} — 2025",
                'ajoute_par':  dd['ajoute_par'],
                'created_at':  date_c,
            }
        )
        created_docs.append(doc)
        if c:
            print(f"   ✔ [{dd['type']}] {dd['title'][:60]}...")

    return created_docs


# =============================================================================
# 👁️  5. CONSULTATIONS, FAVORIS & HISTORIQUE ACTIONS
# =============================================================================

def seed_consultations_favoris():
    from apps.users.models import User
    from apps.etudiant.models import Etudiant
    from apps.documents.models import Document
    from apps.consultations.models import Consultation
    from apps.documents.models import Favori
    from logs.models import HistoriqueActionService

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
        ('etu.kouassi@etud-ci.edu', [
            ('Cours — Le contrôle par voie', 'VUE', 420, True),
            ('Cours — La responsabilité', 'VUE', 360, True),
            ('Examen 2024 — Contentieux constitutionnel', 'VUE', 180, True),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 600, False),
        ]),
        ('etu.traore@etud-ci.edu', [
            ('Cours — La procédure du contentieux civil', 'VUE', 500, True),
            ('Cours — Contentieux pénal', 'VUE', 310, False),
            ('Examen 2024 — Contentieux administratif', 'VUE', 240, True),
            ('Thèse — Le contentieux électoral', 'VUE', 720, True),
        ]),
        ('etu.yao@etud-ci.edu', [
            ('Cours — Voies d\'exécution', 'VUE', 280, False),
            ('Cours — Arbitrage régional', 'VUE', 450, True),
            ('Examen 2024 — Droit de l\'arbitrage', 'VUE', 200, True),
            ('Mémoire — Le recours en annulation', 'VUE', 530, False),
        ]),
        ('etu.coulibaly@etud-ci.edu', [
            ('Cours — Les grands principes du contentieux international', 'VUE', 390, True),
            ('Cours — La classification du formalisme', 'VUE', 260, True),
            ('Examen 2024 — Contentieux international pénal', 'VUE', 300, True),
            ('Thèse — L\'effectivité des décisions', 'VUE', 810, True),
        ]),
        ('etu.gbagbo@etud-ci.edu', [
            ('Cours — Contentieux de la Cour Internationale', 'VUE', 340, False),
            ('Cours — Le contentieux des sociétés', 'VUE', 290, True),
            ('Mémoire — La preuve électronique', 'VUE', 480, True),
            ('Examen 2024 — Contentieux international public', 'VUE', 150, False),
        ]),
        # M2
        ('etu.ouattara@etud-ci.edu', [
            ('Cours — Contentieux électoral', 'VUE', 520, True),
            ('Cours — Arbitrage régional', 'VUE', 410, True),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 900, True),
            ('Thèse — Le contentieux électoral', 'VUE', 660, True),
        ]),
        ('etu.koffi@etud-ci.edu', [
            ('Cours — Les grands principes du contentieux international', 'VUE', 430, True),
            ('Examen 2024 — Contentieux international pénal', 'VUE', 370, True),
            ('Mémoire — Le recours en annulation', 'VUE', 580, False),
            ('Thèse — L\'effectivité des décisions', 'VUE', 750, False),
        ]),
        ('etu.n_goran@etud-ci.edu', [
            ('Cours — La classification du formalisme', 'VUE', 300, True),
            ('Mémoire — La preuve électronique', 'VUE', 680, True),
            ('Examen 2024 — Droit de l\'arbitrage', 'VUE', 220, True),
            ('Cours — Arbitrage régional', 'VUE', 490, False),
        ]),
        ('etu.bamba@etud-ci.edu', [
            ('Thèse — Le contentieux électoral', 'VUE', 840, True),
            ('Cours — Contentieux électoral', 'VUE', 360, True),
            ('Examen 2024 — Contentieux constitutionnel', 'VUE', 190, False),
            ('Cours — Le contrôle par voie', 'VUE', 440, False),
        ]),
        ('etu.ahui@etud-ci.edu', [
            ('Thèse — L\'effectivité des décisions', 'VUE', 920, True),
            ('Cours — Voies d\'exécution', 'VUE', 260, False),
            ('Mémoire — L\'arbitrage OHADA', 'VUE', 510, True),
            ('Examen 2024 — Contentieux administratif', 'VUE', 280, True),
        ]),
    ]

    # ── Recherches effectuées ─────────────────────────────────────────────────
    recherches = [
        ('etu.kouassi@etud-ci.edu',  'arbitrage OHADA',          -20),
        ('etu.traore@etud-ci.edu',   'contentieux civil',         -18),
        ('etu.yao@etud-ci.edu',      'procédures d\'urgence',     -15),
        ('etu.coulibaly@etud-ci.edu','preuve électronique',        -12),
        ('etu.gbagbo@etud-ci.edu',   'contentieux international',  -10),
        ('etu.ouattara@etud-ci.edu', 'mémoire arbitrage',          -8),
        ('etu.koffi@etud-ci.edu',    'examen droit pénal',         -6),
        ('etu.n_goran@etud-ci.edu',  'rédaction actes juridiques', -5),
        ('etu.bamba@etud-ci.edu',    'contentieux électoral',      -4),
        ('etu.ahui@etud-ci.edu',     'CEDEAO droits homme',        -3),
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
    from logs.models import HistoriqueActionService as HAS

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
            details={'type_otp': 'email', 'tentatives': 2}
        )
        nb_logs += 1

    # Activation TOTP (admin & biblio)
    for staff_user in [admin_user, biblio]:
        HAS.log_totp(user=staff_user, statut='succes')
        nb_logs += 1

    # Actions documents par le bibliothécaire
    for doc in tous_docs:
        HAS.log_document('AJOUT', user=biblio, document=doc, ip='192.168.0.1')
        nb_logs += 1

    # Modifications de document par l'admin
    if tous_docs:
        HAS.log_document(
            'MODIFICATION', user=admin_user, document=tous_docs[0],
            details={'champ_modifie': 'description', 'ancienne_valeur': 'v1', 'nouvelle_valeur': 'v2'}
        )
        nb_logs += 1

    # Création d'utilisateurs par l'admin
    for etu_user in tous_etudiants[:3]:
        HAS.log_utilisateur('CREATION', auteur=admin_user, cible_user=etu_user)
        nb_logs += 1

    # Déconnexions
    for user in tous_etudiants[:5]:
        HAS.log_deconnexion(user=user, ip='192.168.1.30')
        nb_logs += 1

    print(f"   ✔ {nb_logs} entrées insérées dans MongoDB")


# =============================================================================
# 🚀  POINT D'ENTRÉE
# =============================================================================

if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    seed_all()