"""
=============================================================================
 config/swagger_config.py
 Configuration drf-spectacular — Swagger UI + ReDoc
 Coller le contenu de SPECTACULAR_SETTINGS dans settings.py
=============================================================================
"""

SPECTACULAR_SETTINGS = {
    # ── Informations générales ────────────────────────────────────────────────
    'TITLE':   'Bibliothèque Universitaire — API',
    'VERSION': '1.0.0',
    'DESCRIPTION': """
# API Bibliothèque Universitaire

API REST complète de la bibliothèque universitaire — Stack DRF + JWT + 2FA TOTP.

---

## Authentification par rôle

| Rôle | Identifiant | Étape 2FA |
|------|-------------|-----------|
| **Étudiant** | Matricule + Mot de passe | Google Authenticator (TOTP) |
| **Bibliothécaire** | Email + Mot de passe | Google Authenticator (TOTP) |
| **Administrateur** | Email + Mot de passe | Google Authenticator (TOTP) |

## Flux de connexion (2 étapes pour tous)

```
┌─────────────────────────────────────────────────────────────┐
│  ÉTUDIANT                                                    │
│  POST /api/auth/etudiant/login/        → retourne user_id   │
│  POST /api/auth/etudiant/totp/verify/  → retourne JWT       │
├─────────────────────────────────────────────────────────────┤
│  BIBLIOTHÉCAIRE                                              │
│  POST /api/auth/bibliothecaire/login/        → user_id      │
│  POST /api/auth/bibliothecaire/totp/verify/  → JWT          │
├─────────────────────────────────────────────────────────────┤
│  ADMINISTRATEUR                                              │
│  POST /api/auth/admin/login/        → user_id               │
│  POST /api/auth/admin/totp/verify/  → JWT                   │
└─────────────────────────────────────────────────────────────┘
```

## Utiliser le token JWT

Après connexion, passez l'`access` token dans chaque requête :
```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

Le token expire en **15 minutes**. Rafraîchissez-le avec `/api/auth/token/refresh/`.

---
    """,

    'CONTACT': {'name': 'Support API', 'email': 'admin@universite-ci.edu'},
    'LICENSE': {'name': 'Propriétaire — Université CI'},

    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': '🛠 Développement local'},
        {'url': 'https://api.bibliotheque-ci.edu', 'description': '🚀 Production'},
    ],

    # ── Sécurité ──────────────────────────────────────────────────────────────
    'SECURITY': [{'BearerAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type':         'http',
                'scheme':       'bearer',
                'bearerFormat': 'JWT',
                'description':  'Token JWT obtenu après connexion en 2 étapes.',
            }
        }
    },

    # ── Tags groupés par rôle ─────────────────────────────────────────────────
    'TAGS': [
        # Auth par rôle
        {'name': 'Auth — Étudiant',       'description': '🎓 Connexion étudiant : matricule + password + TOTP'},
        {'name': 'Auth — Bibliothécaire',  'description': '📖 Connexion bibliothécaire : email + password + TOTP'},
        {'name': 'Auth — Administrateur',  'description': '🔑 Connexion administrateur : email + password + TOTP'},
        # Actions communes
        {'name': 'Auth — Configuration 2FA','description': '🔧 Setup Google Authenticator (Admin + Biblio)'},
        {'name': 'Auth — OTP Email',        'description': '📧 Codes OTP par email (activation, reset, etc.)'},
        {'name': 'Auth — Mot de passe',     'description': '🔄 Réinitialisation du mot de passe'},
        {'name': 'Auth — Tokens JWT',       'description': '🔑 Refresh token et déconnexion'},
        # Ressources
        {'name': 'Utilisateurs',     'description': '👤 CRUD utilisateurs'},
        {'name': 'Étudiants',        'description': '🎓 Profils étudiants, activation, expiration'},
        {'name': 'Bibliothécaires',  'description': '📖 Profils bibliothécaires'},
        {'name': 'Filières',         'description': '🏫 Filières universitaires'},
        {'name': 'Niveaux',          'description': '📊 Niveaux (L1-L2-L3-M1-M2-DOCTORAT avec spécialité)'},
        {'name': 'Spécialités',      'description': '🎯 Spécialités L1/L2/L3/M1/M2/DOCTORAT'},
        {'name': 'UE',               'description': '📚 Unités d\'Enseignement (coef auto)'},
        {'name': 'ECUE',             'description': '📝 Éléments Constitutifs d\'UE'},
        {'name': 'Documents',        'description': '📄 Cours, Examens, Mémoires, Thèses'},
        {'name': 'Favoris',          'description': '⭐ Favoris des étudiants'},
        {'name': 'Consultations',    'description': '👁️ Historique de consultations'},
        {'name': 'Historique',       'description': '📋 Logs d\'actions MongoDB'},
    ],

    # ── Assets (sidecar — pas de CDN externe) ─────────────────────────────────
    'SWAGGER_UI_DIST':      'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST':           'SIDECAR',

    # ── Swagger UI ─────────────────────────────────────────────────────────────
    'SWAGGER_UI_SETTINGS': {
        'deepLinking':              True,
        'persistAuthorization':     True,   # token conservé après refresh page
        'displayOperationId':       False,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth':  2,
        'docExpansion':             'list', # groupes repliés par défaut
        'filter':                   True,   # barre de recherche
        'tryItOutEnabled':          True,   # "Try it out" activé par défaut
        'syntaxHighlight':          {'activate': True, 'theme': 'monokai'},
    },

    # ── ReDoc ──────────────────────────────────────────────────────────────────
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton':       False,
        'disableSearch':            False,
        'expandResponses':          '200,201',
        'requiredPropsFirst':       True,
        'sortPropsAlphabetically':  False,
        'noAutoAuth':               False,
        'pathInMiddlePanel':        True,   # URL dans le panneau central
    },

    # ── Options ────────────────────────────────────────────────────────────────
    'SERVE_INCLUDE_SCHEMA':         False,
    'COMPONENT_SPLIT_REQUEST':      True,
    'SORT_OPERATIONS':              False,
    'ENUM_GENERATE_CHOICE_DESCRIPTION': True,
    'POSTPROCESSING_HOOKS': ['drf_spectacular.hooks.postprocess_schema_enums'],
}


# =============================================================================
# 📌  URLS À AJOUTER DANS config/urls.py
# =============================================================================
"""
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # ── Documentation ──────────────────────────────────────
    path('api/schema/',  SpectacularAPIView.as_view(),         name='schema'),
    path('api/docs/',    SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',   SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    # ── Auth — 3 flux séparés ──────────────────────────────
    path('api/auth/',    include('apps.users.urls')),

    # ── Ressources ─────────────────────────────────────────
    path('api/users/',   include('apps.users.urls.user_urls')),
    ...
]
"""


# =============================================================================
# 📌  INSTALLED_APPS À AJOUTER DANS settings.py
# =============================================================================
"""
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'safedelete',
    'corsheaders',
    ...
]
"""
