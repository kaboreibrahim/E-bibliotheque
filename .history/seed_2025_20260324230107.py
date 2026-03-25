# """
# =============================================================================
#  BIBLIOTHÈQUE UNIVERSITAIRE — fixtures/seed_2025.py
#  Données de test 2025 — Master Droit des Contentieux
 
#  Commande : python seed_2025.py
#             ou python manage.py seed_2025
#             ou appeler seed_all() depuis le shell Django
# =============================================================================
# """

# import uuid
# from datetime import timedelta, datetime
# from django.utils import timezone
# from django.contrib.auth.hashers import make_password


# def seed_all():
#     seed_filieres_niveaux()
#     seed_ues_ecues()
#     seed_utilisateurs()
#     seed_documents()
#     seed_consultations_favoris()
#     print("\n✅ SEED 2025 TERMINÉ AVEC SUCCÈS !\n")


# # =============================================================================
# # 🏫  1. FILIÈRES & NIVEAUX
# # =============================================================================

# def seed_filieres_niveaux():
#     from apps.filiere.models import Filiere
#     from apps.niveau.models import Niveau

#     print("📚 Création filières & niveaux...")

#     filiere, _ = Filiere.objects.get_or_create(
#         name="Droit des Contentieux",
#         defaults={'id': uuid.UUID('aaaaaaaa-0001-0001-0001-000000000001')}
#     )

#     niveaux_data = ['L1', 'L2', 'L3', 'M1', 'M2']
#     niveaux = {}
#     for n in niveaux_data:
#         obj, _ = Niveau.objects.get_or_create(
#             filiere=filiere, name=n
#         )
#         niveaux[n] = obj

#     print(f"   ✔ Filière : {filiere.name}")
#     print(f"   ✔ Niveaux : {', '.join(niveaux_data)}")
#     return filiere, niveaux


# # =============================================================================
# # 📖  2. UEs & ECUEs (issues des images)
# # =============================================================================

# def seed_ues_ecues():
#     from apps.ue.models import UE
#     from apps.filiere.models import Filiere
#     from apps.niveau.models import Niveau

#     print("\n📖 Création UEs & ECUEs Master Droit des Contentieux 2025...")

#     filiere  = Filiere.objects.get(name="Droit des Contentieux")
#     m1       = Niveau.objects.get(filiere=filiere, name='M1')
#     m2       = Niveau.objects.get(filiere=filiere, name='M2')

#     # ── Semestre 1 (M1) ───────────────────────────────────────────────────────
#     ues_s1 = [
#         {'code': 'COC2102', 'name': 'Contentieux constitutionnel',          'coef': 2.00},
#         {'code': 'COA2101', 'name': 'Contentieux administratif',            'coef': 2.00},
#         {'code': 'CCI2103', 'name': 'Contentieux civil',                    'coef': 2.00},
#         {'code': 'COF2104', 'name': 'Contentieux fiscal',                   'coef': 1.50},
#         {'code': 'CPN2105', 'name': 'Contentieux pénal',                    'coef': 1.50},
#     ]

#     # ── Semestre 2 (M1) ───────────────────────────────────────────────────────
#     ues_s2 = [
#         {'code': 'CIP2201', 'name': 'Contentieux international public',     'coef': 2.00},
#         {'code': 'CIE2202', 'name': 'Contentieux international économique', 'coef': 2.00},
#         {'code': 'CCM2203', 'name': 'Contentieux commercial',               'coef': 1.50},
#         {'code': 'VEX2204', 'name': "Voies d'exécution et procédure d'urgence", 'coef': 1.50},
#         {'code': 'DPR2206', 'name': 'Droit de la preuve',                   'coef': 1.00},
#     ]

#     # ── Semestre 3 (M2) ───────────────────────────────────────────────────────
#     ues_s3 = [
#         {'code': 'CPB2301', 'name': 'Contentieux interne public spécialisé','coef': 2.00},
#         {'code': 'CIS2302', 'name': 'Contentieux international spécialisé', 'coef': 2.00},
#         {'code': 'DER2303', 'name': "Droit de l'arbitrage",                 'coef': 2.00},
#         {'code': 'DIC2304', 'name': 'Contentieux international pénal',      'coef': 2.00},
#         {'code': 'RAC2305', 'name': "Rédaction d'actes",                    'coef': 1.50},
#         {'code': 'MET2306', 'name': "Méthodologie d'élaboration",           'coef': 1.00},
#     ]

#     # ── Semestre 4 (M2) ───────────────────────────────────────────────────────
#     ues_s4 = [
#         {'code': 'TCC2307', 'name': 'Mémoire',                              'coef': 4.00},
#     ]

#     for ue_data in ues_s1 + ues_s2:
#         ue, created = UE.objects.get_or_create(
#             code=ue_data['code'],
#             defaults={'name': ue_data['name'], 'coef': ue_data['coef']}
#         )
#         ue.niveaux.add(m1)
#         if created:
#             print(f"   ✔ UE M1 : {ue.code} — {ue.name}")

#     for ue_data in ues_s3 + ues_s4:
#         ue, created = UE.objects.get_or_create(
#             code=ue_data['code'],
#             defaults={'name': ue_data['name'], 'coef': ue_data['coef']}
#         )
#         ue.niveaux.add(m2)
#         if created:
#             print(f"   ✔ UE M2 : {ue.code} — {ue.name}")


# # =============================================================================
# # 👥  3. UTILISATEURS (Admin + Biblio + Étudiants)
# # =============================================================================

# def seed_utilisateurs():
#     from apps.users.models import User
#     from apps.users.models import Etudiant
#     from apps.users.models import Bibliothecaire
#     from apps.filiere.models import Filiere
#     from apps.niveau.models import Niveau

#     print("\n👥 Création des utilisateurs 2025...")

#     filiere = Filiere.objects.get(name="Droit des Contentieux")
#     m1      = Niveau.objects.get(filiere=filiere, name='M1')
#     m2      = Niveau.objects.get(filiere=filiere, name='M2')

#     # ── Administrateur ────────────────────────────────────────────────────────
#     admin, created = User.objects.get_or_create(
#         email='admin@universite-ci.edu',
#         defaults={
#             'first_name': 'Kouamé',
#             'last_name':  'BROU',
#             'phone':      '+2250701000001',
#             'user_type':  User.UserType.ADMINISTRATEUR,
#             'is_staff':   True,
#             'is_superuser': True,
#             'is_active':  True,
#             'is_2fa_enabled': True,
#             'password':   make_password('Admin@2025!'),
#         }
#     )
#     if created:
#         print(f"   ✔ Admin : {admin.email}")

#     # ── Bibliothécaires ───────────────────────────────────────────────────────
#     biblios_data = [
#         {
#             'email':      'biblio.kone@universite-ci.edu',
#             'first_name': 'Mariam',
#             'last_name':  'KONÉ',
#             'phone':      '+2250701000002',
#             'badge':      'BIB-2025-001',
#         },
#         {
#             'email':      'biblio.diallo@universite-ci.edu',
#             'first_name': 'Seydou',
#             'last_name':  'DIALLO',
#             'phone':      '+2250701000003',
#             'badge':      'BIB-2025-002',
#         },
#     ]

#     for bd in biblios_data:
#         user, created = User.objects.get_or_create(
#             email=bd['email'],
#             defaults={
#                 'first_name':     bd['first_name'],
#                 'last_name':      bd['last_name'],
#                 'phone':          bd['phone'],
#                 'user_type':      User.UserType.BIBLIOTHECAIRE,
#                 'is_staff':       True,
#                 'is_active':      True,
#                 'is_2fa_enabled': True,
#                 'password':       make_password('Biblio@2025!'),
#             }
#         )
#         Bibliothecaire.objects.get_or_create(
#             user=user,
#             defaults={
#                 'badge_number':          bd['badge'],
#                 'date_prise_poste':      datetime(2025, 1, 6).date(),
#                 'peut_gerer_documents':  True,
#                 'peut_gerer_utilisateurs': True,
#             }
#         )
#         if created:
#             print(f"   ✔ Biblio : {user.email}")

#     # ── Étudiants M1 ─────────────────────────────────────────────────────────
#     etudiants_m1 = [
#         {'email': 'etu.kouassi@etud-ci.edu',   'first_name': 'Adjoua',   'last_name': 'KOUASSI',   'phone': '+2250701001001'},
#         {'email': 'etu.traore@etud-ci.edu',    'first_name': 'Ibrahim',  'last_name': 'TRAORÉ',    'phone': '+2250701001002'},
#         {'email': 'etu.yao@etud-ci.edu',       'first_name': 'Brice',    'last_name': 'YAO',       'phone': '+2250701001003'},
#         {'email': 'etu.coulibaly@etud-ci.edu', 'first_name': 'Fatou',    'last_name': 'COULIBALY', 'phone': '+2250701001004'},
#         {'email': 'etu.gbagbo@etud-ci.edu',    'first_name': 'Olivia',   'last_name': 'GBAGBO',    'phone': '+2250701001005'},
#     ]

#     # ── Étudiants M2 ─────────────────────────────────────────────────────────
#     etudiants_m2 = [
#         {'email': 'etu.ouattara@etud-ci.edu',  'first_name': 'Salimata', 'last_name': 'OUATTARA',  'phone': '+2250701002001'},
#         {'email': 'etu.koffi@etud-ci.edu',     'first_name': 'Jean-Marc','last_name': 'KOFFI',     'phone': '+2250701002002'},
#         {'email': 'etu.n_goran@etud-ci.edu',   'first_name': 'Rachel',   'last_name': "N'GORAN",   'phone': '+2250701002003'},
#         {'email': 'etu.bamba@etud-ci.edu',     'first_name': 'Moussa',   'last_name': 'BAMBA',     'phone': '+2250701002004'},
#         {'email': 'etu.ahui@etud-ci.edu',      'first_name': 'Prisca',   'last_name': 'AHUI',      'phone': '+2250701002005'},
#     ]

#     activation_base = timezone.now() - timedelta(days=10)  # activés il y a 10 jours

#     for ed in etudiants_m1:
#         user, created = User.objects.get_or_create(
#             email=ed['email'],
#             defaults={
#                 'first_name': ed['first_name'],
#                 'last_name':  ed['last_name'],
#                 'phone':      ed['phone'],
#                 'user_type':  User.UserType.ETUDIANT,
#                 'is_active':  True,
#                 'password':   make_password('Etudiant@2025!'),
#             }
#         )
#         Etudiant.objects.get_or_create(
#             user=user,
#             defaults={
#                 'filiere':           filiere,
#                 'niveau':            m1,
#                 'annee_inscription': 2025,
#                 'compte_active_le':  activation_base,
#                 'compte_expire_le':  activation_base + timedelta(days=30),
#                 'nb_reactivations':  0,
#             }
#         )
#         if created:
#             print(f"   ✔ Étudiant M1 : {user.get_full_name()} ({user.matricule})")

#     for ed in etudiants_m2:
#         user, created = User.objects.get_or_create(
#             email=ed['email'],
#             defaults={
#                 'first_name': ed['first_name'],
#                 'last_name':  ed['last_name'],
#                 'phone':      ed['phone'],
#                 'user_type':  User.UserType.ETUDIANT,
#                 'is_active':  True,
#                 'password':   make_password('Etudiant@2025!'),
#             }
#         )
#         Etudiant.objects.get_or_create(
#             user=user,
#             defaults={
#                 'filiere':           filiere,
#                 'niveau':            m2,
#                 'annee_inscription': 2025,
#                 'compte_active_le':  activation_base,
#                 'compte_expire_le':  activation_base + timedelta(days=30),
#                 'nb_reactivations':  0,
#             }
#         )
#         if created:
#             print(f"   ✔ Étudiant M2 : {user.get_full_name()} ({user.matricule})")


# # =============================================================================
# # 📄  4. DOCUMENTS (Cours, Examens, Mémoires, Thèses)
# # =============================================================================

# def seed_documents():
#     from apps.documents.models import Document
#     from apps.ue.models import UE
#     from apps.users.models import User
#     from apps.filiere.models import Filiere
#     from apps.niveau.models import Niveau

#     print("\n📄 Création des documents 2025...")

#     filiere  = Filiere.objects.get(name="Droit des Contentieux")
#     m1       = Niveau.objects.get(filiere=filiere, name='M1')
#     m2       = Niveau.objects.get(filiere=filiere, name='M2')
#     biblio   = User.objects.get(email='biblio.kone@universite-ci.edu')
#     admin    = User.objects.get(email='admin@universite-ci.edu')

#     docs_data = [

#         # ── COURS M1 Semestre 1 ───────────────────────────────────────────────
#         {
#             'title':    'Cours — Le contrôle par voie d\'action',
#             'type':     'COURS',
#             'ue_code':  'COC2102',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Pr. ASSI Jean-Baptiste',
#             'ajoute_par': biblio,
#             'jours_avant': 90,
#         },
#         {
#             'title':    'Cours — La responsabilité administrative',
#             'type':     'COURS',
#             'ue_code':  'COA2101',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Dr. KONAN Adjoua Marie',
#             'ajoute_par': biblio,
#             'jours_avant': 85,
#         },
#         {
#             'title':    'Cours — La procédure du contentieux civil',
#             'type':     'COURS',
#             'ue_code':  'CCI2103',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Pr. YAPI Kouamé',
#             'ajoute_par': biblio,
#             'jours_avant': 80,
#         },
#         {
#             'title':    'Cours — Contentieux pénal national',
#             'type':     'COURS',
#             'ue_code':  'CPN2105',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Dr. DIOMANDÉ Saliou',
#             'ajoute_par': biblio,
#             'jours_avant': 75,
#         },

#         # ── COURS M1 Semestre 2 ───────────────────────────────────────────────
#         {
#             'title':    'Cours — Contentieux de la Cour Internationale de Justice',
#             'type':     'COURS',
#             'ue_code':  'CIP2201',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Pr. TOURÉ Issiaka',
#             'ajoute_par': biblio,
#             'jours_avant': 60,
#         },
#         {
#             'title':    'Cours — Le contentieux des sociétés commerciales',
#             'type':     'COURS',
#             'ue_code':  'CCM2203',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Dr. BONI Clarisse',
#             'ajoute_par': biblio,
#             'jours_avant': 55,
#         },
#         {
#             'title':    'Cours — Voies d\'exécution',
#             'type':     'COURS',
#             'ue_code':  'VEX2204',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Dr. GNANGUI Pamela',
#             'ajoute_par': biblio,
#             'jours_avant': 50,
#         },

#         # ── COURS M2 Semestre 3 ───────────────────────────────────────────────
#         {
#             'title':    'Cours — Contentieux électoral',
#             'type':     'COURS',
#             'ue_code':  'CPB2301',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Pr. ASSI Jean-Baptiste',
#             'ajoute_par': biblio,
#             'jours_avant': 45,
#         },
#         {
#             'title':    'Cours — Arbitrage régional et national',
#             'type':     'COURS',
#             'ue_code':  'DER2303',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Pr. KOFFI Edmond',
#             'ajoute_par': biblio,
#             'jours_avant': 40,
#         },
#         {
#             'title':    'Cours — Les grands principes du contentieux international pénal',
#             'type':     'COURS',
#             'ue_code':  'DIC2304',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Dr. COULIBALY Nathalie',
#             'ajoute_par': biblio,
#             'jours_avant': 38,
#         },
#         {
#             'title':    'Cours — La classification du formalisme écrit et verbal',
#             'type':     'COURS',
#             'ue_code':  'RAC2305',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Dr. CAMARA Bintou',
#             'ajoute_par': biblio,
#             'jours_avant': 35,
#         },

#         # ── EXAMENS ───────────────────────────────────────────────────────────
#         {
#             'title':    'Examen 2024 — Contentieux constitutionnel (S1)',
#             'type':     'EXAMEN',
#             'ue_code':  'COC2102',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Pr. ASSI Jean-Baptiste',
#             'ajoute_par': admin,
#             'jours_avant': 30,
#         },
#         {
#             'title':    'Examen 2024 — Contentieux administratif (S1)',
#             'type':     'EXAMEN',
#             'ue_code':  'COA2101',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Dr. KONAN Adjoua Marie',
#             'ajoute_par': admin,
#             'jours_avant': 28,
#         },
#         {
#             'title':    'Examen 2024 — Contentieux international public (S2)',
#             'type':     'EXAMEN',
#             'ue_code':  'CIP2201',
#             'niveau':   m1,
#             'auteur':   '',
#             'encadreur':'Pr. TOURÉ Issiaka',
#             'ajoute_par': admin,
#             'jours_avant': 25,
#         },
#         {
#             'title':    'Examen 2024 — Droit de l\'arbitrage (S3)',
#             'type':     'EXAMEN',
#             'ue_code':  'DER2303',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Pr. KOFFI Edmond',
#             'ajoute_par': admin,
#             'jours_avant': 20,
#         },
#         {
#             'title':    'Examen 2024 — Contentieux international pénal (S3)',
#             'type':     'EXAMEN',
#             'ue_code':  'DIC2304',
#             'niveau':   m2,
#             'auteur':   '',
#             'encadreur':'Dr. COULIBALY Nathalie',
#             'ajoute_par': admin,
#             'jours_avant': 18,
#         },

#         # ── MÉMOIRES ─────────────────────────────────────────────────────────
#         {
#             'title':    'Mémoire — L\'arbitrage OHADA face aux juridictions étatiques',
#             'type':     'MEMOIRE',
#             'ue_code':  'TCC2307',
#             'niveau':   m2,
#             'auteur':   'OUATTARA Salimata',
#             'encadreur':'Pr. KOFFI Edmond',
#             'ajoute_par': admin,
#             'jours_avant': 15,
#         },
#         {
#             'title':    'Mémoire — Le recours en annulation devant le Conseil d\'État ivoirien',
#             'type':     'MEMOIRE',
#             'ue_code':  'TCC2307',
#             'niveau':   m2,
#             'auteur':   'KOFFI Jean-Marc',
#             'encadreur':'Dr. KONAN Adjoua Marie',
#             'ajoute_par': admin,
#             'jours_avant': 12,
#         },
#         {
#             'title':    'Mémoire — La preuve électronique dans le contentieux commercial',
#             'type':     'MEMOIRE',
#             'ue_code':  'TCC2307',
#             'niveau':   m2,
#             'auteur':   "N'GORAN Rachel",
#             'encadreur':'Dr. BONI Clarisse',
#             'ajoute_par': admin,
#             'jours_avant': 10,
#         },

#         # ── THÈSES ────────────────────────────────────────────────────────────
#         {
#             'title':    'Thèse — Le contentieux électoral en Afrique de l\'Ouest : étude comparée',
#             'type':     'THESE',
#             'ue_code':  'CPB2301',
#             'niveau':   m2,
#             'auteur':   'BAMBA Moussa',
#             'encadreur':'Pr. ASSI Jean-Baptiste',
#             'ajoute_par': admin,
#             'jours_avant': 8,
#         },
#         {
#             'title':    'Thèse — L\'effectivité des décisions de la COUR CEDEAO des droits de l\'homme',
#             'type':     'THESE',
#             'ue_code':  'CIS2302',
#             'niveau':   m2,
#             'auteur':   'AHUI Prisca',
#             'encadreur':'Pr. TOURÉ Issiaka',
#             'ajoute_par': admin,
#             'jours_avant': 5,
#         },
#     ]

#     created_docs = []
#     for dd in docs_data:
#         ue      = UE.objects.filter(code=dd['ue_code']).first()
#         date_c  = timezone.now() - timedelta(days=dd['jours_avant'])
#         doc, c  = Document.objects.get_or_create(
#             title=dd['title'],
#             defaults={
#                 'type':        dd['type'],
#                 'filiere':     filiere,
#                 'niveau':      dd['niveau'],
#                 'ue':          ue,
#                 'auteur':      dd['auteur'],
#                 'encadreur':   dd['encadreur'],
#                 'file_path':   f"documents/{dd['type'].lower()}/{dd['title'][:30].replace(' ','_')}.pdf",
#                 'description': f"Document de {dd['type'].lower()} — {dd['ue_code']} — 2025",
#                 'ajoute_par':  dd['ajoute_par'],
#                 'created_at':  date_c,
#             }
#         )
#         created_docs.append(doc)
#         if c:
#             print(f"   ✔ [{dd['type']}] {dd['title'][:60]}...")

#     return created_docs


# # =============================================================================
# # 👁️  5. CONSULTATIONS, FAVORIS & HISTORIQUE ACTIONS
# # =============================================================================

# def seed_consultations_favoris():
#     from apps.users.models import User
#     from apps.users.models import Etudiant
#     from apps.documents.models import Document
#     from apps.consultations.models import Consultation
#     from apps.favoris.models import Favori
#     from apps.history.models import HistoriqueActionService

#     print("\n👁️  Création des consultations, favoris & logs 2025...")

#     # Récupérer tous les étudiants
#     etudiants = list(Etudiant.objects.select_related('user').all())
#     # Récupérer tous les documents
#     tous_docs  = list(Document.objects.all())
#     biblio     = User.objects.get(email='biblio.kone@universite-ci.edu')
#     admin_user = User.objects.get(email='admin@universite-ci.edu')

#     if not etudiants or not tous_docs:
#         print("   ⚠️  Pas d'étudiants ou de documents trouvés, skip.")
#         return

#     # ── Interactions par étudiant ─────────────────────────────────────────────
#     interactions = [
#         # (email_etudiant, [(titre_partiel_doc, type_action, duree_sec, en_favori)])
#         ('etu.kouassi@etud-ci.edu', [
#             ('Cours — Le contrôle par voie', 'VUE', 420, True),
#             ('Cours — La responsabilité', 'VUE', 360, True),
#             ('Examen 2024 — Contentieux constitutionnel', 'VUE', 180, True),
#             ('Mémoire — L\'arbitrage OHADA', 'VUE', 600, False),
#         ]),
#         ('etu.traore@etud-ci.edu', [
#             ('Cours — La procédure du contentieux civil', 'VUE', 500, True),
#             ('Cours — Contentieux pénal', 'VUE', 310, False),
#             ('Examen 2024 — Contentieux administratif', 'VUE', 240, True),
#             ('Thèse — Le contentieux électoral', 'VUE', 720, True),
#         ]),
#         ('etu.yao@etud-ci.edu', [
#             ('Cours — Voies d\'exécution', 'VUE', 280, False),
#             ('Cours — Arbitrage régional', 'VUE', 450, True),
#             ('Examen 2024 — Droit de l\'arbitrage', 'VUE', 200, True),
#             ('Mémoire — Le recours en annulation', 'VUE', 530, False),
#         ]),
#         ('etu.coulibaly@etud-ci.edu', [
#             ('Cours — Les grands principes du contentieux international', 'VUE', 390, True),
#             ('Cours — La classification du formalisme', 'VUE', 260, True),
#             ('Examen 2024 — Contentieux international pénal', 'VUE', 300, True),
#             ('Thèse — L\'effectivité des décisions', 'VUE', 810, True),
#         ]),
#         ('etu.gbagbo@etud-ci.edu', [
#             ('Cours — Contentieux de la Cour Internationale', 'VUE', 340, False),
#             ('Cours — Le contentieux des sociétés', 'VUE', 290, True),
#             ('Mémoire — La preuve électronique', 'VUE', 480, True),
#             ('Examen 2024 — Contentieux international public', 'VUE', 150, False),
#         ]),
#         # M2
#         ('etu.ouattara@etud-ci.edu', [
#             ('Cours — Contentieux électoral', 'VUE', 520, True),
#             ('Cours — Arbitrage régional', 'VUE', 410, True),
#             ('Mémoire — L\'arbitrage OHADA', 'VUE', 900, True),
#             ('Thèse — Le contentieux électoral', 'VUE', 660, True),
#         ]),
#         ('etu.koffi@etud-ci.edu', [
#             ('Cours — Les grands principes du contentieux international', 'VUE', 430, True),
#             ('Examen 2024 — Contentieux international pénal', 'VUE', 370, True),
#             ('Mémoire — Le recours en annulation', 'VUE', 580, False),
#             ('Thèse — L\'effectivité des décisions', 'VUE', 750, False),
#         ]),
#         ('etu.n_goran@etud-ci.edu', [
#             ('Cours — La classification du formalisme', 'VUE', 300, True),
#             ('Mémoire — La preuve électronique', 'VUE', 680, True),
#             ('Examen 2024 — Droit de l\'arbitrage', 'VUE', 220, True),
#             ('Cours — Arbitrage régional', 'VUE', 490, False),
#         ]),
#         ('etu.bamba@etud-ci.edu', [
#             ('Thèse — Le contentieux électoral', 'VUE', 840, True),
#             ('Cours — Contentieux électoral', 'VUE', 360, True),
#             ('Examen 2024 — Contentieux constitutionnel', 'VUE', 190, False),
#             ('Cours — Le contrôle par voie', 'VUE', 440, False),
#         ]),
#         ('etu.ahui@etud-ci.edu', [
#             ('Thèse — L\'effectivité des décisions', 'VUE', 920, True),
#             ('Cours — Voies d\'exécution', 'VUE', 260, False),
#             ('Mémoire — L\'arbitrage OHADA', 'VUE', 510, True),
#             ('Examen 2024 — Contentieux administratif', 'VUE', 280, True),
#         ]),
#     ]

#     # ── Recherches effectuées ─────────────────────────────────────────────────
#     recherches = [
#         ('etu.kouassi@etud-ci.edu',  'arbitrage OHADA',          -20),
#         ('etu.traore@etud-ci.edu',   'contentieux civil',         -18),
#         ('etu.yao@etud-ci.edu',      'procédures d\'urgence',     -15),
#         ('etu.coulibaly@etud-ci.edu','preuve électronique',        -12),
#         ('etu.gbagbo@etud-ci.edu',   'contentieux international',  -10),
#         ('etu.ouattara@etud-ci.edu', 'mémoire arbitrage',          -8),
#         ('etu.koffi@etud-ci.edu',    'examen droit pénal',         -6),
#         ('etu.n_goran@etud-ci.edu',  'rédaction actes juridiques', -5),
#         ('etu.bamba@etud-ci.edu',    'contentieux électoral',      -4),
#         ('etu.ahui@etud-ci.edu',     'CEDEAO droits homme',        -3),
#     ]

#     nb_consultations = 0
#     nb_favoris       = 0
#     nb_recherches    = 0

#     for email_etu, actions in interactions:
#         try:
#             user = User.objects.get(email=email_etu)
#             etu  = Etudiant.objects.get(user=user)
#         except (User.DoesNotExist, Etudiant.DoesNotExist):
#             continue

#         for i, (titre_partiel, type_action, duree, en_favori) in enumerate(actions):
#             # Trouver le document correspondant
#             doc = next((d for d in tous_docs if titre_partiel.lower() in d.title.lower()), None)
#             if not doc:
#                 continue

#             # Créer la consultation
#             debut = timezone.now() - timedelta(days=15 - i, hours=i * 2)
#             fin   = debut + timedelta(seconds=duree)

#             _, created = Consultation.objects.get_or_create(
#                 user=user,
#                 document=doc,
#                 debut_consultation=debut,
#                 defaults={
#                     'type_consultation': type_action,
#                     'fin_consultation':  fin,
#                     'duree_secondes':    duree,
#                     'ip_address':        f'192.168.1.{10 + i}',
#                     'user_agent':        'Mozilla/5.0 (Windows NT 10.0) Chrome/120.0',
#                 }
#             )
#             if created:
#                 nb_consultations += 1

#             # Créer le favori si demandé
#             if en_favori:
#                 _, fav_created = Favori.objects.get_or_create(
#                     etudiant=etu,
#                     document=doc
#                 )
#                 if fav_created:
#                     nb_favoris += 1

#     # ── Recherches ────────────────────────────────────────────────────────────
#     for email_etu, query, jours in recherches:
#         try:
#             user = User.objects.get(email=email_etu)
#         except User.DoesNotExist:
#             continue

#         _, created = Consultation.objects.get_or_create(
#             user=user,
#             type_consultation='RECHERCHE',
#             recherche_query=query,
#             defaults={
#                 'debut_consultation': timezone.now() + timedelta(days=jours),
#                 'ip_address':         '192.168.1.50',
#                 'user_agent':         'Mozilla/5.0 (Android) Mobile',
#             }
#         )
#         if created:
#             nb_recherches += 1

#     print(f"   ✔ {nb_consultations} consultations créées")
#     print(f"   ✔ {nb_favoris} favoris créés")
#     print(f"   ✔ {nb_recherches} recherches créées")

#     # ── Historique actions MongoDB ────────────────────────────────────────────
#     _seed_historique_actions(admin_user, biblio)


# def _seed_historique_actions(admin_user, biblio):
#     """Insère des logs réalistes dans MongoDB."""
#     from apps.users.models import User
#     from apps.documents.models import Document
#     from apps.history.models import HistoriqueActionService as HAS

#     print("\n📋 Insertion logs MongoDB (HistoriqueAction)...")

#     tous_etudiants = list(User.objects.filter(user_type='ETUDIANT'))
#     tous_docs      = list(Document.objects.all()[:5])

#     nb_logs = 0

#     # Connexions des étudiants (7 derniers jours)
#     for i, user in enumerate(tous_etudiants):
#         result = HAS.log_connexion(
#             user=user,
#             statut='succes',
#             ip=f'192.168.1.{20 + i}',
#             ua='Mozilla/5.0 Chrome/120.0'
#         )
#         if result:
#             nb_logs += 1

#     # 3 tentatives de connexion échouées
#     for i, user in enumerate(tous_etudiants[:3]):
#         HAS.log_connexion(user=user, statut='echec', ip='10.0.0.99')
#         nb_logs += 1

#     # Tentatives OTP échouées
#     for user in tous_etudiants[:2]:
#         HAS.log(
#             action=HAS.ACTIONS.OTP_ECHEC,
#             user=user,
#             statut='echec',
#             ip_address='10.0.0.50',
#             details={'type_otp': 'email', 'tentatives': 2}
#         )
#         nb_logs += 1

#     # Activation TOTP (admin & biblio)
#     for staff_user in [admin_user, biblio]:
#         HAS.log_totp(user=staff_user, statut='succes')
#         nb_logs += 1

#     # Actions documents par le bibliothécaire
#     for doc in tous_docs:
#         HAS.log_document('AJOUT', user=biblio, document=doc, ip='192.168.0.1')
#         nb_logs += 1

#     # Modifications de document par l'admin
#     if tous_docs:
#         HAS.log_document(
#             'MODIFICATION', user=admin_user, document=tous_docs[0],
#             details={'champ_modifie': 'description', 'ancienne_valeur': 'v1', 'nouvelle_valeur': 'v2'}
#         )
#         nb_logs += 1

#     # Création d'utilisateurs par l'admin
#     for etu_user in tous_etudiants[:3]:
#         HAS.log_utilisateur('CREATION', auteur=admin_user, cible_user=etu_user)
#         nb_logs += 1

#     # Déconnexions
#     for user in tous_etudiants[:5]:
#         HAS.log_deconnexion(user=user, ip='192.168.1.30')
#         nb_logs += 1

#     print(f"   ✔ {nb_logs} entrées insérées dans MongoDB")


# # =============================================================================
# # 🚀  POINT D'ENTRÉE
# # =============================================================================

# if __name__ == '__main__':
#     import django
#     import os
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
#     django.setup()
#     seed_all()



"""
=============================================================================
 BIBLIOTHEQUE UNIVERSITAIRE - fixtures/seed_2025.py
 Structure adaptee :
   L1/L2/L3  -> Tronc commun Droit General (memes UEs, pas de specialite)
   M1/M2     -> Specialites (Contentieux, Affaires, Public, Prive)
   DOCTORAT  -> Uniquement These (pas d UEs)
=============================================================================
 Lancer : python manage.py shell < fixtures/seed_2025.py
=============================================================================
"""
from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone
from django.contrib.auth.hashers import make_password


def seed_all():
    print("="*60)
    print("  SEED 2025 - BIBLIOTHEQUE UNIVERSITAIRE")
    print("="*60)
    filieres, niveaux = seed_filieres_niveaux()
    types_docs        = seed_types_documents()
    ues, ecues        = seed_ues_ecues(niveaux)
    utilisateurs      = seed_utilisateurs(filieres, niveaux)
    documents         = seed_documents(ues, ecues, types_docs, utilisateurs, niveaux, filieres)
    seed_interactions(utilisateurs, documents)
    print("="*60)
    print("  SEED 2025 TERMINE !")
    print("="*60)


# ===========================================================================
# 1. FILIERES & NIVEAUX
# ===========================================================================
def seed_filieres_niveaux():
    from apps.filiere.models import Filiere
    from apps.niveau.models import Niveau

    print("\n[1/6] Filieres & Niveaux...")
    filieres = {}
    for nom in ['Droit General', 'Droit des Contentieux', 'Droit des Affaires',
                'Droit Public', 'Droit Prive', 'Doctorat en Droit']:
        obj, c = Filiere.objects.get_or_create(name=nom)
        filieres[nom] = obj
        if c: print(f"   + Filiere : {nom}")

    niveaux = {}
    # Tronc commun L1 L2 L3 — filiere unique "Droit General"
    for lvl in ['L1', 'L2', 'L3']:
        obj, c = Niveau.objects.get_or_create(filiere=filieres['Droit General'], name=lvl)
        niveaux[f'TC_{lvl}'] = obj
        if c: print(f"   + Tronc commun {lvl}")

    # Specialites Master M1 M2
    for sp in ['Droit des Contentieux', 'Droit des Affaires', 'Droit Public', 'Droit Prive']:
        for lvl in ['M1', 'M2']:
            obj, c = Niveau.objects.get_or_create(filiere=filieres[sp], name=lvl)
            niveaux[f'{sp}_{lvl}'] = obj
            if c: print(f"   + {sp} {lvl}")

    # Doctorat
    obj, c = Niveau.objects.get_or_create(filiere=filieres['Doctorat en Droit'], name='DOCTORAT')
    niveaux['DOCTORAT'] = obj
    if c: print(f"   + DOCTORAT")

    return filieres, niveaux


# ===========================================================================
# 2. TYPES DOCUMENTS
# ===========================================================================
def seed_types_documents():
    from apps.documents.models import TypeDocument
    print("\n[2/6] Types documents...")
    types = {}
    for val, label in TypeDocument.TypeChoices.choices:
        obj, c = TypeDocument.objects.get_or_create(type=val)
        types[val] = obj
        if c: print(f"   + {label}")
    return types


# ===========================================================================
# 3. UEs & ECUEs — coef_total = somme automatique des coefs ECUE
# ===========================================================================
def seed_ues_ecues(niveaux):
    from apps.documents.models import UE, ECUE
    print("\n[3/6] UEs & ECUEs (avec calcul coef automatique)...")
    ues, ecues = {}, {}

    def make(id_ue, code, name, niv_key, ecues_list):
        ue, _ = UE.objects.get_or_create(
            id_ue=id_ue,
            defaults={'code': code, 'name': name, 'niveau': niveaux.get(niv_key)}
        )
        ues[id_ue] = ue
        for e in ecues_list:
            ecue, _ = ECUE.objects.get_or_create(
                code_ecue=e['code'],
                defaults={
                    'name': e['name'], 'coef': e['coef'], 'ue': ue,
                    'cm': e.get('cm',0), 'td': e.get('td',0), 'tp': e.get('tp',0),
                    'tpe': e.get('tpe',0), 'sem': e.get('sem',0), 'ctt': e.get('ctt',0),
                }
            )
            ecues[e['code']] = ecue
        ue.recalcul_coef_total()  # coef_total = somme des coefs ECUE
        print(f"   + {niv_key:35s} | UE {id_ue} | coef_total={ue.coef_total}")

    # --- TRONC COMMUN L1 ---
    make('DCI1101','DCI1101','Droit Civil I','TC_L1',[
        {'code':'1DCI1101','name':'Les personnes physiques et morales','coef':Decimal('1.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2DCI1101','name':'La famille et les successions',     'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
    ])  # coef_total = 3.0
    make('DCC1102','DCC1102','Droit Constitutionnel','TC_L1',[
        {'code':'1DCC1102','name':"Theorie generale de l'Etat",  'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2DCC1102','name':'Les institutions politiques',  'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
    ])  # coef_total = 3.0
    make('HDD1103','HDD1103','Histoire du Droit','TC_L1',[
        {'code':'1HDD1103','name':'Histoire des institutions',    'coef':Decimal('1.0'),'cm':24,'td':12,'tpe':30,'ctt':66},
        {'code':'2HDD1103','name':'Histoire des sources du droit','coef':Decimal('1.0'),'cm':24,'td':12,'tpe':30,'ctt':66},
    ])  # coef_total = 2.0

    # --- TRONC COMMUN L2 ---
    make('DCI2101','DCI2101','Droit des Obligations','TC_L2',[
        {'code':'1DCI2101','name':'Le contrat : formation et effets',     'coef':Decimal('2.0'),'cm':36,'td':18,'tpe':45,'ctt':99},
        {'code':'2DCI2101','name':'La responsabilite civile delictuelle', 'coef':Decimal('2.0'),'cm':36,'td':18,'tpe':45,'ctt':99},
    ])  # coef_total = 4.0
    make('DPE2102','DPE2102','Droit Penal General','TC_L2',[
        {'code':'1DPE2102','name':"L'infraction penale",'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
        {'code':'2DPE2102','name':'La sanction penale',  'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
    ])  # coef_total = 3.0
    make('DAD2103','DAD2103','Droit Administratif','TC_L2',[
        {'code':'1DAD2103','name':"L'organisation administrative",'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
        {'code':'2DAD2103','name':"L'acte administratif",         'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
    ])  # coef_total = 3.0

    # --- TRONC COMMUN L3 ---
    make('DPR3101','DPR3101','Droit des Proprietes','TC_L3',[
        {'code':'1DPR3101','name':'La propriete individuelle',   'coef':Decimal('2.0'),'cm':36,'td':18,'tpe':45,'ctt':99},
        {'code':'2DPR3101','name':'La propriete intellectuelle', 'coef':Decimal('2.0'),'cm':36,'td':18,'tpe':45,'ctt':99},
    ])  # coef_total = 4.0
    make('DIC3102','DIC3102','Droit International','TC_L3',[
        {'code':'1DIC3102','name':'Droit international public','coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
        {'code':'2DIC3102','name':'Droit international prive', 'coef':Decimal('1.5'),'cm':30,'td':15,'tpe':30,'ctt':75},
    ])  # coef_total = 3.0
    make('PRO3103','PRO3103','Procedure Civile','TC_L3',[
        {'code':'1PRO3103','name':"L'action en justice",  'coef':Decimal('1.0'),'cm':24,'td':12,'tpe':30,'ctt':66},
        {'code':'2PRO3103','name':'Les voies de recours', 'coef':Decimal('1.0'),'cm':24,'td':12,'tpe':30,'ctt':66},
    ])  # coef_total = 2.0

    # --- SPECIALITE CONTENTIEUX M1 (vos images Semestre 1 + 2) ---
    make('COC2102','COC2102','Contentieux constitutionnel','Droit des Contentieux_M1',[
        {'code':'1COC2102','name':"Le controle par voie d'action",   'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2COC2102','name':"Le controle par voie d'exception",'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':30,'ctt':50},
    ])  # coef_total = 3.0
    make('COA2101','COA2101','Contentieux administratif','Droit des Contentieux_M1',[
        {'code':'1COA2101','name':'La responsabilite administrative','coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2COA2101','name':'Le recours en annulation',        'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':30,'ctt':50},
    ])  # coef_total = 3.0
    make('CCI2103','CCI2103','Contentieux civil','Droit des Contentieux_M1',[
        {'code':'1CCI2103','name':'La presentation du tribunal et ses animateurs','coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2CCI2103','name':'La procedure du contentieux civil',            'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':30,'ctt':50},
    ])  # coef_total = 3.0
    make('COF2104','COF2104','Contentieux fiscal','Droit des Contentieux_M1',[
        {'code':'1COF2104','name':'Le recours contentieux fiscal',    'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':30,'ctt':50},
        {'code':'2COF2104','name':'Le recours non contentieux fiscal','coef':Decimal('1.0'),'cm':18,'td':12,'tpe':30,'ctt':50},
    ])  # coef_total = 2.0
    make('CPN2105','CPN2105','Contentieux penal','Droit des Contentieux_M1',[
        {'code':'1CPN2105','name':'Contentieux penal national',      'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':30,'ctt':50},
        {'code':'2CPN2105','name':'Contentieux international penal', 'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':30,'ctt':50},
    ])  # coef_total = 2.0
    make('CIP2201','CIP2201','Contentieux international public','Droit des Contentieux_M1',[
        {'code':'1CIP2201','name':'Contentieux de la Cour Internationale de Justice',          'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2CIP2201','name':'Contentieux du Tribunal International du Droit de la Mer',  'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
    ])  # coef_total = 3.0
    make('CIE2202','CIE2202','Contentieux international economique','Droit des Contentieux_M1',[
        {'code':'1CIE2202','name':'Organe de Reglement des Differends OMC',                   'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2CIE2202','name':'Centre International Reglement Differends (CIRDI)',         'coef':Decimal('1.5'),'cm':18,'td':12,'tpe':45,'ctt':75},
    ])  # coef_total = 3.0
    make('CCM2203','CCM2203','Contentieux commercial','Droit des Contentieux_M1',[
        {'code':'1CCM2203','name':'Le contentieux des societes commerciales',  'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2CCM2203','name':'Le contentieux des commercants individuels','coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
    ])  # coef_total = 2.0
    make('VEX2204','VEX2204',"Voies d'execution et procedure urgence",'Droit des Contentieux_M1',[
        {'code':'1VEX2204','name':"Voies d'execution",    'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2VEX2204','name':"Procedures d'urgence", 'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
    ])  # coef_total = 2.0
    make('DPR2206','DPR2206','Droit de la preuve','Droit des Contentieux_M1',[
        {'code':'1DPR2206','name':'La preuve electronique','coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
        {'code':'2DPR2206','name':"L'expertise judiciaire",'coef':Decimal('1.0'),'cm':18,'td':12,'tpe':45,'ctt':75},
    ])  # coef_total = 2.0

    # --- SPECIALITE CONTENTIEUX M2 (vos images Semestre 3 + 4) ---
    make('CPB2301','CPB2301','Contentieux interne public specialise','Droit des Contentieux_M2',[
        {'code':'1CPB2301','name':'Contentieux electoral','coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
        {'code':'2CPB2301','name':'Contentieux foncier',  'coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
    ])  # coef_total = 4.0
    make('CIS2302','CIS2302','Contentieux international specialise','Droit des Contentieux_M2',[
        {'code':'1CIS2302','name':'Contentieux regional sous regional Droits Homme','coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
        {'code':'2CIS2302','name':"Contentieux international des Droits de l'Homme",'coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
    ])  # coef_total = 4.0
    make('DER2303','DER2303',"Droit de l'arbitrage",'Droit des Contentieux_M2',[
        {'code':'1DER2303','name':'Arbitrage regional et national','coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
        {'code':'2DER2303','name':'Arbitrage international',       'coef':Decimal('1.5'),'cm':12,'sem':8, 'ctt':8},
    ])  # coef_total = 3.5
    make('DIC2304','DIC2304','Contentieux international penal','Droit des Contentieux_M2',[
        {'code':'1DIC2304','name':'Les grands principes du contentieux international penal','coef':Decimal('2.0'),'cm':18,'sem':12,'ctt':12},
        {'code':'2DIC2304','name':'Le deroulement du contentieux international penal',      'coef':Decimal('1.5'),'cm':12,'sem':8, 'ctt':8},
    ])  # coef_total = 3.5
    make('RAC2305','RAC2305',"Redaction d'actes",'Droit des Contentieux_M2',[
        {'code':'1RAC2305','name':'La classification du formalisme ecrit et verbal','coef':Decimal('1.5'),'cm':12,'sem':8,'ctt':8},
        {'code':'2RAC2305','name':'La pratique de la redaction des actes',          'coef':Decimal('1.5'),'cm':12,'sem':8,'ctt':8},
    ])  # coef_total = 3.0
    make('MET2306','MET2306',"Methodologie d'elaboration",'Droit des Contentieux_M2',[
        {'code':'1MET2306','name':'Montage et evaluation de projets','coef':Decimal('1.0'),'cm':12,'sem':8,'ctt':8},
        {'code':'2MET2306','name':'Methodologie de la recherche',    'coef':Decimal('1.0'),'cm':20,'ctt':0},
    ])  # coef_total = 2.0
    make('TCC2307','TCC2307','Memoire professionnel','Droit des Contentieux_M2',[
        {'code':'1TCC2307','name':'Redaction du rapport/memoire professionnel','coef':Decimal('4.0'),'cm':0,'ctt':0},
        {'code':'2TCC2307','name':'Soutenance du rapport/memoire professionnel','coef':Decimal('4.0'),'cm':0,'ctt':0},
    ])  # coef_total = 8.0

    # --- SPECIALITE AFFAIRES ---
    make('SOC3101','SOC3101','Droit des Societes','Droit des Affaires_M1',[
        {'code':'1SOC3101','name':'Constitution et fonctionnement des societes','coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2SOC3101','name':'Dissolution et liquidation des societes',    'coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 4.0
    make('COM3102','COM3102','Droit Commercial','Droit des Affaires_M1',[
        {'code':'1COM3102','name':'Le commercant et les actes de commerce','coef':Decimal('1.5'),'cm':24,'td':12,'tpe':30,'ctt':66},
        {'code':'2COM3102','name':'Le fonds de commerce',                  'coef':Decimal('1.5'),'cm':24,'td':12,'tpe':30,'ctt':66},
    ])  # coef_total = 3.0
    make('OHA3201','OHA3201','Droit OHADA','Droit des Affaires_M2',[
        {'code':'1OHA3201','name':'Les actes uniformes OHADA','coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2OHA3201','name':"L'arbitrage OHADA",        'coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 5.0
    make('MEMA3203','MEMA3203','Memoire Droit des Affaires','Droit des Affaires_M2',[
        {'code':'1MEMA3203','name':'Redaction du memoire', 'coef':Decimal('4.0'),'cm':0,'ctt':0},
        {'code':'2MEMA3203','name':'Soutenance du memoire','coef':Decimal('4.0'),'cm':0,'ctt':0},
    ])  # coef_total = 8.0

    # --- SPECIALITE PUBLIC ---
    make('FIN4101','FIN4101','Finances Publiques','Droit Public_M1',[
        {'code':'1FIN4101','name':"Le budget de l'Etat",   'coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2FIN4101','name':"L'execution budgetaire", 'coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 4.0
    make('SER4201','SER4201','Droit des Services Publics','Droit Public_M2',[
        {'code':'1SER4201','name':'Le regime juridique des services publics','coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2SER4201','name':'La delegation de service public',         'coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 5.0
    make('MEMP4202','MEMP4202','Memoire Droit Public','Droit Public_M2',[
        {'code':'1MEMP4202','name':'Redaction du memoire', 'coef':Decimal('4.0'),'cm':0,'ctt':0},
        {'code':'2MEMP4202','name':'Soutenance du memoire','coef':Decimal('4.0'),'cm':0,'ctt':0},
    ])  # coef_total = 8.0

    # --- SPECIALITE PRIVE ---
    make('FAM5101','FAM5101','Droit de la Famille Approfondi','Droit Prive_M1',[
        {'code':'1FAM5101','name':'Le mariage et ses effets',   'coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2FAM5101','name':"La filiation et l'adoption",'coef':Decimal('2.0'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 4.0
    make('CON5201','CON5201','Droit des Contrats Speciaux','Droit Prive_M2',[
        {'code':'1CON5201','name':'Les contrats de vente',   'coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
        {'code':'2CON5201','name':'Les contrats de service', 'coef':Decimal('2.5'),'cm':30,'td':15,'tpe':45,'ctt':90},
    ])  # coef_total = 5.0
    make('MEMV5202','MEMV5202','Memoire Droit Prive','Droit Prive_M2',[
        {'code':'1MEMV5202','name':'Redaction du memoire', 'coef':Decimal('4.0'),'cm':0,'ctt':0},
        {'code':'2MEMV5202','name':'Soutenance du memoire','coef':Decimal('4.0'),'cm':0,'ctt':0},
    ])  # coef_total = 8.0

    return ues, ecues


# ===========================================================================
# 4. UTILISATEURS
# ===========================================================================
def seed_utilisateurs(filieres, niveaux):
    from apps.users.models import User
    from apps.etudiant.models import Etudiant
    from apps.bibliothecaire.models import Bibliothecaire
    print("\n[4/6] Utilisateurs 2025...")
    activation = timezone.now() - timedelta(days=10)
    expiration = activation + timedelta(days=30)
    utilisateurs = {'admin': None, 'biblios': [], 'etudiants': []}

    admin, _ = User.objects.get_or_create(
        email='admin@universite-ci.edu',
        defaults={'first_name':'Kouame','last_name':'BROU','phone':'+2250701000001',
                  'user_type':User.UserType.ADMINISTRATEUR,'is_staff':True,'is_superuser':True,
                  'is_active':True,'is_2fa_enabled':True,'password':make_password('Admin@2025!')})
    utilisateurs['admin'] = admin
    print(f"   + Admin : {admin.email}")

    for bd in [
        {'email':'biblio.kone@universite-ci.edu',  'first_name':'Mariam', 'last_name':'KONE',  'phone':'+2250701000002','badge':'BIB-2025-001'},
        {'email':'biblio.diallo@universite-ci.edu','first_name':'Seydou', 'last_name':'DIALLO','phone':'+2250701000003','badge':'BIB-2025-002'},
    ]:
        u, _ = User.objects.get_or_create(email=bd['email'], defaults={
            'first_name':bd['first_name'],'last_name':bd['last_name'],'phone':bd['phone'],
            'user_type':User.UserType.BIBLIOTHECAIRE,'is_staff':True,'is_active':True,
            'is_2fa_enabled':True,'password':make_password('Biblio@2025!')})
        Bibliothecaire.objects.get_or_create(user=u, defaults={
            'badge_number':bd['badge'],'date_prise_poste':date(2025,1,6),
            'peut_gerer_documents':True,'peut_gerer_utilisateurs':True})
        utilisateurs['biblios'].append(u)
        print(f"   + Biblio : {u.email}")

    # (email, prenom, nom, phone, filiere_nom, niveau_key, label)
    etu_data = [
        # Tronc commun — pas de specialite
        ('etu.amani.l1@etud-ci.edu',    'Aminata',  'AMANI',   '+2250702001001','Droit General','TC_L1',                    'L1 Tronc commun'),
        ('etu.berte.l1@etud-ci.edu',    'Berenger', 'BERTE',   '+2250702001002','Droit General','TC_L1',                    'L1 Tronc commun'),
        ('etu.cisse.l2@etud-ci.edu',    'Clement',  'CISSE',   '+2250702002001','Droit General','TC_L2',                    'L2 Tronc commun'),
        ('etu.dembele.l2@etud-ci.edu',  'Daouda',   'DEMBELE', '+2250702002002','Droit General','TC_L2',                    'L2 Tronc commun'),
        ('etu.ettien.l3@etud-ci.edu',   'Elise',    'ETTIEN',  '+2250702003001','Droit General','TC_L3',                    'L3 Tronc commun'),
        ('etu.fofana.l3@etud-ci.edu',   'Fatoumata','FOFANA',  '+2250702003002','Droit General','TC_L3',                    'L3 Tronc commun'),
        # Specialite Contentieux M1 et M2
        ('etu.gbagbo.m1c@etud-ci.edu',  'Gisele',   'GBAGBO',  '+2250702004001','Droit des Contentieux','Droit des Contentieux_M1','M1 Contentieux'),
        ('etu.hauhouot.m1c@etud-ci.edu','Hyacinthe','HAUHOUOT', '+2250702004002','Droit des Contentieux','Droit des Contentieux_M1','M1 Contentieux'),
        ('etu.irie.m2c@etud-ci.edu',    'Ines',     'IRIE',     '+2250702005001','Droit des Contentieux','Droit des Contentieux_M2','M2 Contentieux'),
        ('etu.johnson.m2c@etud-ci.edu', 'Jean-Paul','JOHNSON',  '+2250702005002','Droit des Contentieux','Droit des Contentieux_M2','M2 Contentieux'),
        # Specialite Affaires
        ('etu.kone.m1a@etud-ci.edu',    'Karidja',  'KONE',     '+2250702006001','Droit des Affaires','Droit des Affaires_M1','M1 Affaires'),
        ('etu.meless.m2a@etud-ci.edu',  'Marcelline','MELESS',  '+2250702007001','Droit des Affaires','Droit des Affaires_M2','M2 Affaires'),
        # Specialite Public
        ('etu.nguessan.m1p@etud-ci.edu','NGuessan', 'NGUESSAN', '+2250702008001','Droit Public','Droit Public_M1','M1 Public'),
        ('etu.ouattara.m2p@etud-ci.edu','Oceane',   'OUATTARA', '+2250702009001','Droit Public','Droit Public_M2','M2 Public'),
        # Specialite Prive
        ('etu.pehe.m1v@etud-ci.edu',    'Pelagie',  'PEHE',     '+2250702010001','Droit Prive','Droit Prive_M1','M1 Prive'),
        ('etu.quao.m2v@etud-ci.edu',    'Quentin',  'QUAO',     '+2250702011001','Droit Prive','Droit Prive_M2','M2 Prive'),
        # Doctorat — uniquement these, pas d'UEs
        ('etu.roux.doc@etud-ci.edu',    'Rodrigue', 'ROUX',     '+2250702012001','Doctorat en Droit','DOCTORAT','DOCTORAT'),
    ]

    for email,prenom,nom,phone,filiere_nom,niv_key,label in etu_data:
        u, created = User.objects.get_or_create(email=email, defaults={
            'first_name':prenom,'last_name':nom,'phone':phone,
            'user_type':User.UserType.ETUDIANT,'is_active':True,
            'password':make_password('Etudiant@2025!')})
        Etudiant.objects.get_or_create(user=u, defaults={
            'filiere':filieres.get(filiere_nom), 'niveau':niveaux.get(niv_key),
            'annee_inscription':2025,'compte_active_le':activation,'compte_expire_le':expiration,'nb_reactivations':0})
        if created: print(f"   + [{label}] {prenom} {nom} ({u.matricule})")
        utilisateurs['etudiants'].append(u)
    return utilisateurs


# ===========================================================================
# 5. DOCUMENTS
# ===========================================================================
def seed_documents(ues, ecues, types_docs, utilisateurs, niveaux, filieres):
    from apps.documents.models import Document, DocumentUE
    print("\n[5/6] Documents 2025...")
    biblio = utilisateurs['biblios'][0]
    admin  = utilisateurs['admin']
    docs   = []

    def doc(title, type_key, ue_code, ecue_code, fil_nom, niv_key,
            auteur='', encadreur='', par=None):
        doc_ue = DocumentUE.objects.create(auteur=auteur, encadreur=encadreur)
        d, created = Document.objects.get_or_create(title=title, defaults={
            'type_document': types_docs.get(type_key),
            'ue':            ues.get(ue_code),
            'ecue':          ecues.get(ecue_code),
            'document_ue':   doc_ue,
            'filiere':       filieres.get(fil_nom),
            'niveau':        niveaux.get(niv_key),
            'file_path':     f"documents/{type_key.lower()}/{title[:20].replace(' ','_')}.pdf",
            'description':   f"{type_key} - {ue_code} - 2025",
            'ajoute_par':    par or biblio,
        })
        if created: print(f"   + [{type_key}] {title[:65]}...")
        return d

    # Tronc commun
    docs += [
        doc('Cours - Les personnes physiques et morales','COURS','DCI1101','1DCI1101','Droit General','TC_L1',encadreur='Pr. YAPI Edmond'),
        doc('Cours - Theorie generale de Etat',          'COURS','DCC1102','1DCC1102','Droit General','TC_L1',encadreur='Pr. ASSI Bertin'),
        doc('Cours - Le contrat formation et effets',    'COURS','DCI2101','1DCI2101','Droit General','TC_L2',encadreur='Pr. TOURE Issiaka'),
        doc('Cours - L infraction penale',               'COURS','DPE2102','1DPE2102','Droit General','TC_L2',encadreur='Dr. DIOMANDE Saliou'),
        doc('Cours - L action en justice',               'COURS','PRO3103','1PRO3103','Droit General','TC_L3',encadreur='Pr. BONI Lambert'),
        doc('Cours - La propriete intellectuelle',       'COURS','DPR3101','2DPR3101','Droit General','TC_L3',encadreur='Dr. GNANGUI Paul'),
        doc('Examen 2024 - Droit Civil L1',              'EXAMEN','DCI1101','1DCI1101','Droit General','TC_L1',encadreur='Pr. YAPI Edmond',   par=admin),
        doc('Examen 2024 - Droit Constitutionnel L1',    'EXAMEN','DCC1102','1DCC1102','Droit General','TC_L1',encadreur='Pr. ASSI Bertin',   par=admin),
        doc('Examen 2024 - Obligations L2',              'EXAMEN','DCI2101','1DCI2101','Droit General','TC_L2',encadreur='Pr. TOURE Issiaka', par=admin),
        doc('Examen 2024 - Procedure Civile L3',         'EXAMEN','PRO3103','1PRO3103','Droit General','TC_L3',encadreur='Pr. BONI Lambert',  par=admin),
    ]
    # Contentieux M1
    docs += [
        doc('Cours - Le controle par voie action',       'COURS','COC2102','1COC2102','Droit des Contentieux','Droit des Contentieux_M1',encadreur='Pr. ASSI Jean-Baptiste'),
        doc('Cours - La responsabilite administrative',  'COURS','COA2101','1COA2101','Droit des Contentieux','Droit des Contentieux_M1',encadreur='Dr. KONAN Adjoua'),
        doc('Cours - Contentieux penal national',        'COURS','CPN2105','1CPN2105','Droit des Contentieux','Droit des Contentieux_M1',encadreur='Dr. DIOMANDE Saliou'),
        doc('Cours - Voies execution',                   'COURS','VEX2204','1VEX2204','Droit des Contentieux','Droit des Contentieux_M1',encadreur='Dr. GNANGUI Pamela'),
        doc('Examen 2024 - Contentieux constitutionnel', 'EXAMEN','COC2102','1COC2102','Droit des Contentieux','Droit des Contentieux_M1',encadreur='Pr. ASSI Jean-Baptiste',par=admin),
    ]
    # Contentieux M2
    docs += [
        doc('Cours - Contentieux electoral',             'COURS','CPB2301','1CPB2301','Droit des Contentieux','Droit des Contentieux_M2',encadreur='Pr. ASSI Jean-Baptiste'),
        doc('Cours - Arbitrage regional et national',    'COURS','DER2303','1DER2303','Droit des Contentieux','Droit des Contentieux_M2',encadreur='Pr. KOFFI Edmond'),
        doc('Cours - Grands principes cont int penal',   'COURS','DIC2304','1DIC2304','Droit des Contentieux','Droit des Contentieux_M2',encadreur='Dr. COULIBALY Nathalie'),
        doc('Examen 2024 - Droit de arbitrage S3',       'EXAMEN','DER2303','1DER2303','Droit des Contentieux','Droit des Contentieux_M2',encadreur='Pr. KOFFI Edmond',par=admin),
        doc('Memoire - Arbitrage OHADA face juridictions','MEMOIRE','TCC2307','1TCC2307','Droit des Contentieux','Droit des Contentieux_M2',auteur='IRIE Ines',par=admin),
        doc('Memoire - Preuve electronique cont comm',   'MEMOIRE','TCC2307','2TCC2307','Droit des Contentieux','Droit des Contentieux_M2',auteur='JOHNSON Jean-Paul',par=admin),
        doc('These - Contentieux electoral Afrique Ouest','THESE','CPB2301','1CPB2301','Droit des Contentieux','Droit des Contentieux_M2',auteur='ROUX Rodrigue',par=admin),
    ]
    # Affaires / Public / Prive
    docs += [
        doc('Cours - Constitution societes commerciales','COURS','SOC3101','1SOC3101','Droit des Affaires','Droit des Affaires_M1',encadreur='Dr. CAMARA Bintou'),
        doc('Cours - Actes uniformes OHADA',             'COURS','OHA3201','1OHA3201','Droit des Affaires','Droit des Affaires_M2',encadreur='Pr. TOURE Issiaka'),
        doc('Memoire - Redressement judiciaire PME OHADA','MEMOIRE','MEMA3203','1MEMA3203','Droit des Affaires','Droit des Affaires_M2',auteur='MELESS Marcelline',par=admin),
        doc('Cours - Budget de Etat',                    'COURS','FIN4101','1FIN4101','Droit Public','Droit Public_M1',encadreur='Dr. BROU Sylvestre'),
        doc('Memoire - Delegation de service public',    'MEMOIRE','MEMP4202','1MEMP4202','Droit Public','Droit Public_M2',auteur='OUATTARA Oceane',par=admin),
        doc('Cours - Le mariage et ses effets',          'COURS','FAM5101','1FAM5101','Droit Prive','Droit Prive_M1',encadreur='Pr. YAPI Kouame'),
        doc('Memoire - Filiation familles recomposees',  'MEMOIRE','MEMV5202','1MEMV5202','Droit Prive','Droit Prive_M2',auteur='QUAO Quentin',par=admin),
    ]
    print(f"\n   Total : {len([d for d in docs if d])} documents")
    return [d for d in docs if d]


# ===========================================================================
# 6. CONSULTATIONS, FAVORIS & LOGS MONGODB
# ===========================================================================
def seed_interactions(utilisateurs, documents):
    from apps.etudiant.models import Etudiant
    from apps.consultations.models import Consultation
    from apps.documents.models import Favori
    from logs.models import HistoriqueActionService as HAS
    print("\n[6/6] Consultations, favoris & logs MongoDB...")
    etudiants_users = utilisateurs['etudiants']
    biblio = utilisateurs['biblios'][0]
    admin  = utilisateurs['admin']
    nb_cons = nb_fav = nb_rech = nb_logs = 0

    for i, user in enumerate(etudiants_users):
        try: etu = Etudiant.objects.get(user=user)
        except: continue

        # Docs de sa filiere (priorite) + 1 hors filiere
        docs_fil  = [d for d in documents if d.filiere == etu.filiere][:3]
        docs_hors = [d for d in documents if d.filiere != etu.filiere][:1]

        for j, doc in enumerate(docs_fil + docs_hors):
            debut = timezone.now() - timedelta(days=20-i-j, hours=j)
            duree = 200 + i*60 + j*40
            _, c = Consultation.objects.get_or_create(
                user=user, document=doc, debut_consultation=debut,
                defaults={'type_consultation':'VUE','fin_consultation':debut+timedelta(seconds=duree),
                          'duree_secondes':duree,'ip_address':f'192.168.{i+1}.{j+10}',
                          'user_agent':'Mozilla/5.0 Chrome/120.0'})
            if c: nb_cons += 1
            if j < 2:
                _, fc = Favori.objects.get_or_create(etudiant=etu, document=doc)
                if fc: nb_fav += 1

        terme = f"droit {etu.filiere.name.split()[-1].lower()}" if etu.filiere else "droit"
        _, rc = Consultation.objects.get_or_create(
            user=user, type_consultation='RECHERCHE', recherche_query=terme,
            defaults={'debut_consultation':timezone.now()-timedelta(days=5+i),'ip_address':f'192.168.{i+1}.1'})
        if rc: nb_rech += 1

    for u in etudiants_users[:10]:
        if HAS.log_connexion(user=u, statut='succes', ip='192.168.0.1'): nb_logs += 1
    for u in etudiants_users[:3]:
        if HAS.log_connexion(user=u, statut='echec', ip='10.0.0.99'): nb_logs += 1
    for u in etudiants_users[:2]:
        HAS.log(action=HAS.ACTIONS.OTP_ECHEC, user=u, statut='echec',
                ip_address='10.0.0.50', details={'type_otp':'email','tentatives':2})
        nb_logs += 1
    for d in documents[:6]:
        HAS.log_document('AJOUT', user=biblio, document=d, ip='192.168.0.1')
        nb_logs += 1
    HAS.log_document('MODIFICATION', user=admin, document=documents[0],
                     details={'champ':'description','avant':'v1','apres':'v2'})
    nb_logs += 1
    for u in etudiants_users[:5]:
        HAS.log_utilisateur('CREATION', auteur=admin, cible_user=u)
        nb_logs += 1
    print(f"   + {nb_cons} consultations | {nb_fav} favoris | {nb_rech} recherches | {nb_logs} logs MongoDB")


# ===========================================================================
# POINT D ENTREE
# ===========================================================================
if __name__ == '__main__':
    import django, os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

seed_all()