# RAPPORT GLOBAL D'AUDIT

## Sécurité — Performance — API — Architecture — Base de données

**Projet :** E-BIBLIO / PERED (Plateforme d'Étude et de Recherche en Droit)
**Version auditée :** branche `master`, état au 2026-09-20
**Stack :** Django 6.0.1 / DRF 3.16.1 / djangorestframework-simplejwt 5.5.1 / PostgreSQL / MongoDB (historique) / Flutter (mobile, en cours)
**Environnement :** Développement local (déploiement cible : cPanel)
**Auditeur :** Claude (Sonnet 5) + développeur du projet

> **Ce document est vivant.** Il est mis à jour au fil du cycle `AUDIT → DISCUSSION → VALIDATION → MODIFICATION → TEST → MESURE`. Aucune action n'est appliquée avant validation explicite (`VALIDER`) dans la conversation.

> ⚠️ **Avant toute chose** : trois constats de la section 5 (SEC-001, SEC-002, SEC-003) exposent des secrets réels (clé Django, identifiants base de données, identifiants MongoDB Atlas, mot de passe SMTP Gmail) directement dans le dépôt Git. Ce sont des actions **hors cycle de code** (rotation de identifiants côté fournisseurs) qu'il faut traiter en priorité, indépendamment du reste de l'audit — voir section 5.

---

# 1. Résumé exécutif

## 1.1 État général

| Domaine          | État | Nombre de problèmes identifiés |
| ---------------- | :--: | ------------------------------: |
| Sécurité         |  🔴  | 6 (dont 3 critiques) |
| Authentification |  🟠  | 1 (absence de rate limiting) |
| Autorisation     |  🔴  | 3 (IDOR Favoris/Consultations, accès vertical données de référence) |
| API / Endpoints  |  🟠  | voir section 4 (échantillon) |
| Base de données  |  🟡  | 2 (agrégation en Python, index manquants) |
| Performance      |  🟡  | 1 confirmé (stats stockage), autres à mesurer |
| Architecture     |  🟢  | cohérente (repository/service/serializer/view), pas de refonte nécessaire |
| Frontend         |  ⬜  | app Flutter encore en construction, pas encore auditable en usage réel |
| Configuration    |  🔴  | `DEBUG=True` forcé, secrets en dur, `.gitignore` absent |
| Tests            |  🟡  | tests unitaires présents sur `apps/users` (TOTP, profil, export), aucun test de permission/IDOR |

### Résumé

Le code métier (couche repository/service/serializer/view) est globalement propre et cohérent d'une app à l'autre — ce n'est pas le principal problème. Les points bloquants sont concentrés sur **trois zones précises** : (1) des secrets réels commités dans Git et un `DEBUG` forcé à `True` en dur, (2) une absence quasi totale de contrôle d'accès par objet (IDOR) sur `Favoris` et `Consultations`, et (3) un contrôle d'accès vertical manquant sur les données de référence (Filière/Niveau/Spécialité/UE), où n'importe quel utilisateur authentifié — y compris un étudiant — peut créer/modifier/supprimer ces données. Ces trois zones sont indépendantes les unes des autres et peuvent être corrigées séparément, dans l'ordre de priorité de la section 12.

---

# 2. Statistiques de l'audit

| Indicateur                         | Nombre (constaté) |
| ----------------------------------- | -----------------: |
| Applications Django analysées       | 12 (`users`, `documents`, `filiere`, `niveau`, `specialites`, `ue`, `favoris`, `consultations`, `history`, `annee_academique`, `core`) |
| Models analysés en détail           | ~15 (`User`, `Etudiant`, `Bibliothecaire`, `PersonneExterne`, `Document`, `TypeDocument`, `UE`, `ECUE`, `Filiere`, `Niveau`, `Specialite`, `Favori`, `Consultation`, `AnneeAcademique`) |
| Endpoints recensés (approx., via `manage.py spectacular`) | ~90 |
| Endpoints analysés en détail dans ce rapport | 14 (échantillon à haut risque, section 4) |
| Failles critiques (🔴)              | 6 |
| Failles hautes (🟠)                 | 3 |
| Problèmes moyens (🟡)               | 4 |
| Problèmes faibles (🟢)              | 2 |
| Optimisations proposées             | 2 |
| Actions validées                    | 0 |
| Actions réalisées                   | 0 |

*Le reste de l'inventaire (endpoints CRUD standards non listés individuellement, modèles secondaires comme `ECUE`, `HistoriqueAction`) suit tous le même pattern que les endpoints équivalents déjà couverts — ils seront détaillés à la demande plutôt que dupliqués ici.*

---

# 3. Architecture actuelle

## 3.1 Structure

```text
E-BIBLIO/
├── core/                      # settings, urls, wsgi/asgi, swagger config, mongo_client
├── apps/
│   ├── users/                 # User + profils (Etudiant, Bibliothecaire, PersonneExterne...), auth JWT+TOTP
│   ├── annee_academique/      # Année universitaire courante (ajoutée cette session)
│   ├── filiere/ niveau/ specialites/ ue/   # Données de référence académiques
│   ├── documents/             # Documents (upload, stream, stats)
│   ├── favoris/                # Favoris étudiant ↔ document
│   ├── consultations/         # Historique de vues/recherches (PostgreSQL)
│   └── history/               # Journal d'actions (MongoDB)
├── mobile/e_bibliotheque/     # App Flutter (en construction)
└── media/, staticfiles/       # Fichiers uploadés / statiques
```

Chaque app métier suit le même découpage à 4 couches : `models.py` → `repositories.py` (accès DB statique) → `services.py` (règles métier, `ValidationError`) → `views.py` (ViewSet DRF + doc `drf-spectacular`) + `serializers.py`. C'est un pattern cohérent et répété partout, ce qui facilite l'audit et la correction (une faille trouvée dans un pattern se retrouve souvent à l'identique ailleurs — cf. SEC-004/SEC-005 ci-dessous, qui sont le même bug dans deux apps différentes).

## 3.2 Flux applicatif

```text
Flutter (mobile) / Swagger UI
    ↓
DRF Router (rest_framework.routers.DefaultRouter par app)
    ↓
Authentication : JWTAuthentication (rest_framework_simplejwt)
    ↓
Permissions : IsAuthenticated (défaut global) + permissions custom par action (get_permissions)
    ↓
ViewSet (souvent viewsets.ViewSet "manuel", pas ModelViewSet)
    ↓
Service (règles métier, lève django.core.exceptions.ValidationError)
    ↓
Repository (staticmethods, QuerySet Django ORM)
    ↓
PostgreSQL (données métier) + MongoDB (apps.history, journal d'actions)
```

## 3.3 Dépendances importantes entre modules

- `Document` dépend de `Filiere`/`Niveau`/`Specialite`/`ECUE` (FK `SET_NULL`) — cohérent, pas de suppression en cascade dangereuse ici.
- `Etudiant` dépend de `Filiere`/`Niveau`/`Specialite` (FK `SET_NULL`) et de `AnneeAcademique` (indirectement, via la logique de service à la création — pas de FK directe).
- `Favori` et `Consultation` dépendent de `Document` avec `on_delete=CASCADE` pour `Favori.document` — la suppression (soft-delete via `safedelete`) d'un document masque donc aussi ses favoris associés selon la politique `SOFT_DELETE_CASCADE`, ce qui est cohérent.
- `apps.history` écrit dans MongoDB indépendamment de la transaction PostgreSQL en cours (`HistoriqueActionService.log*`) — **aucun rollback croisé possible** : si l'écriture MongoDB échoue après une écriture PostgreSQL réussie (ou l'inverse), il n'y a pas de mécanisme de compensation. Risque faible en pratique (le log est accessoire), mais à noter (voir TECH-001, section 18).

---

# 4. Inventaire des endpoints (échantillon à risque)

| ID      | Méthode | Endpoint                                | Auth | Permission                     | Rôle réellement autorisé | Risque | Performance |
| ------- | ------- | ---------------------------------------- | :--: | ------------------------------- | ------------------------- | :----: | :----------: |
| API-001 | POST    | `/api/favoris/`                          | Oui  | `IsAuthenticated`               | **N'importe quel compte** (devrait être : l'étudiant lui-même) | 🔴 | 🟢 |
| API-002 | GET     | `/api/favoris/?etudiant={id}`            | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟢 |
| API-003 | DELETE  | `/api/favoris/{id}/`                     | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟢 |
| API-004 | GET     | `/api/consultations/?user={id}`          | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟡 (pas de pagination visible sur ce filtre) |
| API-005 | GET     | `/api/consultations/en-cours/?user={id}` | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟢 |
| API-006 | DELETE  | `/api/consultations/{id}/`               | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟢 |
| API-007 | POST    | `/api/filieres/`                         | Oui  | `IsAuthenticated`               | **N'importe quel compte** (devrait être Admin) | 🔴 | 🟢 |
| API-008 | DELETE  | `/api/filieres/{id}/`                    | Oui  | `IsAuthenticated`               | **N'importe quel compte** | 🔴 | 🟢 |
| API-009 | POST/DELETE | `/api/niveaux/`, `/api/specialites/`, `/api/ues/` (+ détail) | Oui | `IsAuthenticated` | **N'importe quel compte** | 🔴 | 🟢 |
| API-010 | POST    | `/api/documents/`                        | Oui  | `IsAuthenticated` + `CanManageDocuments` | Admin / Bibliothécaire autorisé | 🟠 (upload non validé, voir SEC-008) | 🟡 |
| API-011 | GET     | `/api/documents/{id}/fichier/`           | Oui  | `IsAuthenticated`               | Tout utilisateur ayant accès au document | 🟠 (Content-Type reflété tel que fourni à l'upload) | 🟢 |
| API-012 | GET     | `/api/documents/stats/dashboard/`        | Oui  | `IsAuthenticated` + `CanManageDocuments` | Admin / Bibliothécaire | 🟢 | 🟡 (voir PERF-001) |
| API-013 | POST    | `/api/auth/etudiant/login/` (+ biblio/admin/externe) | Non | Publique (login) | Public | 🟠 (pas de rate limiting, voir SEC-007) | 🟢 |
| API-014 | POST    | `/api/etudiants/`                        | Oui  | `IsAuthenticated` + `IsAdminOrBibliothecaire` | Admin / Bibliothécaire habilité | 🟢 (correctement gardé) | 🟢 |

*Les endpoints CRUD non listés (bibliothécaires, personnes externes, chercheurs, ECUE, types de documents...) suivent l'un des deux patterns ci-dessus : soit `CanManageDocuments`/`IsAdministrateur` correctement appliqué (comme API-010, API-014, et les endpoints `annee_academique` ajoutés cette session), soit `IsAuthenticated` seul sans restriction supplémentaire (comme API-007 à API-009). Je peux produire l'inventaire exhaustif des ~90 endpoints à la demande — je l'ai volontairement limité ici à l'échantillon représentatif pour ne pas noyer les vrais problèmes sous une table de 90 lignes majoritairement identiques.*

---

# 5. Registre global des problèmes

## SEC-001 — Secrets réels commités dans Git (`.env` suivi, aucun `.gitignore`)

**Catégorie :** Sécurité
**Gravité :** 🔴 Critique
**Statut :** 🔧 Partiellement appliquée (ACT-002 fait le 2026-09-20 : `.gitignore` créé, `.env` retiré du suivi Git, `.env.example` ajouté. **Reste à faire, hors code, par le développeur** : rotation du mot de passe PostgreSQL, du mot de passe MongoDB Atlas, et régénération de `SECRET_KEY` — ces identifiants sont restés exposés dans l'historique Git tant qu'un nettoyage d'historique n'est pas fait.)
**Fichier :** `.env`, `core/settings.py`
**Ligne :** tout le fichier `.env`
**Endpoint :** N/A (configuration globale)

### Constat
Il n'existe **aucun fichier `.gitignore`** à la racine du projet. Le fichier `.env` est suivi par Git (`git ls-files` le confirme) et contient en clair : `SECRET_KEY` Django, les identifiants PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`), et les identifiants MongoDB Atlas (`MONGO_URI`, `MONGO_USER`, `MONGO_PASSWORD`). Il contient aussi, en commentaire, un jeu d'identifiants PostgreSQL cPanel d'un **autre projet** (`c2730729c_sourcing` / mot de passe en clair).

### Preuve
```
$ git ls-files | grep -E "^\.env$"
.env
$ git log --oneline -- .env
f67a17a first commit
```

### Impact
Toute personne ayant accès au dépôt (collaborateur, service CI, fuite du repo) obtient un accès direct à la base de données de production/dev et au cluster MongoDB Atlas, et peut forger des JWT valides pour n'importe quel utilisateur (la `SECRET_KEY` sert de `SIGNING_KEY` JWT, cf. `SIMPLE_JWT`). C'est la faille la plus grave du projet.

### Cause
`.env` créé avant l'ajout d'un `.gitignore`, jamais retiré du suivi Git ensuite.

### Solution proposée
1. **Immédiat, hors code** : faire tourner (changer) le mot de passe PostgreSQL, le mot de passe MongoDB Atlas, et régénérer `SECRET_KEY` — ces identifiants doivent être considérés compromis dès maintenant, indépendamment de toute action sur le code.
2. Créer un `.gitignore` (`.env`, `env/`, `__pycache__/`, `*.pyc`, `media/`, `.history/`, `staticfiles/`).
3. Retirer `.env` du suivi Git (`git rm --cached .env`) sans le supprimer du disque.
4. Fournir un `.env.example` avec les noms de variables mais sans valeurs.
5. Nettoyer l'historique Git si le dépôt est ou sera poussé sur un remote partagé (`git filter-repo` ou BFG) — à discuter séparément, c'est une opération destructive sur l'historique.

### Alternatives
1. Garder `.env` en clair mais restreindre l'accès au dépôt (insuffisant : la rotation des secrets reste indispensable).
2. Migrer vers un gestionnaire de secrets (Vault, variables d'environnement cPanel directement) — plus robuste à moyen terme.

### Risque de régression
Faible pour les étapes 2-4 (changements Git, pas de code applicatif touché). Moyen pour la rotation des identifiants (nécessite de mettre à jour `.env` sur chaque environnement en même temps que la rotation, sans quoi l'app ne démarre plus).

### Tests nécessaires
- [x] `python manage.py check` après retrait de `.env` du suivi Git — OK
- [ ] `python manage.py check` après mise à jour de `.env` local avec les nouveaux identifiants (rotation restante)
- [ ] Connexion applicative à PostgreSQL et MongoDB après rotation
- [ ] Vérifier qu'aucun token JWT émis avant la rotation de `SECRET_KEY` ne reste accepté (rotation de clé invalide tous les tokens existants — prévenir les utilisateurs connectés)

### Décision
**🔧 PARTIELLEMENT VALIDÉE ET APPLIQUÉE** — `.gitignore`/`.env.example`/retrait du suivi Git faits (ACT-002). Rotation des identifiants encore en attente côté développeur.

---

## SEC-002 — `DEBUG = True` forcé en dur, quel que soit l'environnement

**Catégorie :** Sécurité / Configuration
**Gravité :** 🔴 Critique
**Statut :** ✔️ Terminée (ACT-003, 2026-09-20)
**Fichier :** `core/settings.py`
**Ligne :** 355
**Endpoint :** Toute l'API (pages d'erreur Django/DRF)

### Constat
```python
# ligne 41
DEBUG = env_bool('DEBUG', default=False)
...
# ligne 355
DEBUG=True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```
La ligne 355 réaffecte `DEBUG` à `True` de façon inconditionnelle, **après** la lecture correcte depuis `.env` à la ligne 41. Résultat : quelle que soit la valeur de `DEBUG` dans `.env`, l'application tourne toujours avec `DEBUG=True`, y compris si elle est déployée telle quelle sur cPanel.

### Impact
Avec `DEBUG=True`, toute exception non gérée renvoie la page de debug Django complète : code source, valeurs de variables locales, requêtes SQL exécutées, chemin absolu du serveur, et — plus grave ici — les **valeurs de `settings`** peuvent apparaître dans le traceback (dont potentiellement `SECRET_KEY`, mots de passe DB si affichés dans un contexte d'erreur DB). C'est une exposition d'information critique, exploitable par n'importe quel visiteur externe en provoquant une erreur 500.

### Cause
Ligne ajoutée manifestement pendant un debug local et jamais retirée.

### Solution proposée
Supprimer purement et simplement la ligne 355 (`DEBUG=True`), et garder uniquement la lecture depuis l'environnement à la ligne 41. Vérifier que `.env` (local) définit `DEBUG=True` pour le poste de dev, et que la configuration de production définira `DEBUG=False`.

### Alternatives
Aucune pertinente — c'est un bug de configuration sans ambiguïté.

### Risque de régression
Faible : en local, il suffit de s'assurer que `.env` contient `DEBUG=True` pour ne rien changer au confort de développement.

### Tests nécessaires
- [x] `python manage.py check` — OK après suppression de la ligne
- [ ] `python manage.py check --deploy` avec `DEBUG=False` en environnement de test
- [ ] Provoquer une erreur 500 volontaire en local avec `DEBUG=False` et vérifier qu'une page générique s'affiche (pas de traceback)

### Décision
**✔️ VALIDÉE ET APPLIQUÉE** — ligne 355 supprimée, `DEBUG` suit désormais uniquement `.env`.

---

## SEC-003 — Identifiants SMTP Gmail en clair dans le code source

**Catégorie :** Sécurité
**Gravité :** 🔴 Critique
**Statut :** ✔️ Terminée (2026-09-20) — correctif différent de la proposition initiale, voir note ci-dessous
**Fichier :** `core/settings.py`
**Ligne :** 360-361

### Constat
```python
EMAIL_HOST_USER = 'ibrahimkabore025@gmail.com'
EMAIL_HOST_PASSWORD = 'hrwc jlvv ksqy gfeq'
```
Un mot de passe d'application Gmail est écrit en clair dans un fichier suivi par Git.

### Impact
Compromission possible du compte Gmail (au minimum, envoi d'emails au nom de ce compte via SMTP) par quiconque a accès au dépôt.

### Cause
Configuration email codée en dur au lieu de passer par `.env`/`decouple.config(...)`, comme le reste des secrets du projet (qui utilise déjà `python-decouple` correctement pour `SECRET_KEY`/`DB_*`).

### Solution proposée
1. Révoquer immédiatement ce mot de passe d'application dans les paramètres de sécurité Google (hors code).
2. Générer un nouveau mot de passe d'application et le placer dans `.env` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`), lu via `config(...)` comme le reste.

### Alternatives
Passer par un service transactionnel (SendGrid, Mailgun...) plutôt que le SMTP Gmail personnel — plus robuste pour la production, mais changement plus large, à traiter séparément si souhaité.

### Risque de régression
Faible — remplacement mécanique d'une valeur en dur par une lecture `.env`.

### Tests nécessaires
- [x] Envoi d'un email de test (`python manage.py sendtestemail`) — confirmé fonctionnel par le développeur

### Décision
**✔️ VALIDÉE ET APPLIQUÉE** — au lieu de simplement régénérer le mot de passe d'application Gmail, le projet est passé à un compte SMTP cPanel dédié (`it@otl-bulkliquid.com`, `mail.otl-bulkliquid.com:465` en SSL implicite). `core/settings.py` lit désormais `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_USE_SSL`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` depuis `.env` (plus aucune valeur en dur dans le code). Le mot de passe Gmail original reste à révoquer côté Google si ce n'est pas déjà fait — il n'est plus utilisé par l'application mais reste un identifiant qui a été exposé.

---

## SEC-004 — IDOR / BOLA complet sur `Favori` (apps/favoris)

**Catégorie :** Sécurité — Autorisation
**Gravité :** 🔴 Critique
**Statut :** ✔️ Terminée (ACT-005, 2026-09-20/21) — décision retenue : strictement privé, y compris pour Admin/Bibliothécaire
**Fichier :** `apps/favoris/views.py`, `apps/favoris/services.py`
**Ligne :** `views.py` 73-201 ; `services.py` 37-107
**Endpoint :** `GET/POST /api/favoris/`, `GET/DELETE /api/favoris/{id}/`, `POST /api/favoris/toggle/`, `GET /api/favoris/verifier/`

### Constat
Aucune méthode de `FavoriViewSet` (`list`, `create`, `retrieve`, `destroy`, `toggle`, `verifier`) ne vérifie que l'`etudiant` ciblé correspond à `request.user`. Le champ `etudiant` est un UUID librement fourni par le client dans le body ou en query param. `request.user` n'est utilisé qu'en tant qu'`acteur` pour le **log d'audit** (`HistoriqueActionService`), jamais pour l'autorisation.

### Preuve
```python
# apps/favoris/views.py
def create(self, request):
    serializer = FavoriCreateSerializer(data=request.data)  # {"etudiant": <uuid>, "document": <uuid>}
    ...
    favori = _service.ajouter_favori(
        etudiant_id=str(vd["etudiant"]),   # <- vient du client, jamais comparé à request.user
        ...
    )

def destroy(self, request, pk=None):
    _service.supprimer_favori(pk, acteur=request.user, ...)  # <- pas de vérif que ce favori appartient à request.user
```
Concrètement, un étudiant A authentifié peut :
- lire les favoris de l'étudiant B : `GET /api/favoris/?etudiant=<uuid-B>`
- ajouter un favori pour B : `POST /api/favoris/` avec `{"etudiant": "<uuid-B>", "document": "..."}`
- supprimer n'importe quel favori d'un autre étudiant en devinant/énumérant son UUID : `DELETE /api/favoris/{id}/`

### Impact
Atteinte à la confidentialité (savoir ce qu'un autre étudiant consulte) et à l'intégrité (modifier les favoris d'autrui). Sévérité élevée car exploitable par **tout compte authentifié**, sans droits particuliers.

### Cause
Absence de toute permission par objet (`IsOwner`-like) sur cette ressource ; le design actuel fait confiance à la valeur envoyée par le client.

### Solution proposée
- Ne plus accepter `etudiant` en entrée pour un étudiant connecté : le déduire systématiquement de `request.user.profil_etudiant`.
- Pour `retrieve`/`destroy`/`toggle`, vérifier que `favori.etudiant_id == request.user.profil_etudiant.id` (sauf si `request.user` est Admin/Bibliothécaire, qui peuvent légitimement consulter tous les favoris à des fins de gestion — à confirmer avec toi si c'est un besoin réel).
- Ajouter une permission dédiée (`IsOwnerEtudiantOrAdmin`) réutilisable.

### Alternatives
1. Garder le paramètre `etudiant` mais le restreindre : autorisé seulement si `request.user` est Admin/Bibliothécaire, sinon forcé à `request.user.profil_etudiant.id`.
2. Séparer complètement les endpoints "mes favoris" (implicite, sans paramètre) des endpoints de gestion admin (avec paramètre explicite, permission stricte).

### Risque de régression
Moyen : si le frontend/app mobile envoie déjà systématiquement l'UUID de l'étudiant connecté (comportement légitime actuel), le changement est transparent. Si un écran admin utilise ce même endpoint pour consulter les favoris d'un autre étudiant, il faudra l'adapter.

### Tests nécessaires
- [x] Étudiant A ne peut pas lister les favoris de B — vérifié (`apps/favoris/tests.py`, `FavoriIdorTests`)
- [x] Étudiant A ne peut pas créer un favori pour B (le `etudiant` envoyé est ignoré, favori créé pour A) — vérifié
- [x] Étudiant A ne peut pas supprimer un favori de B (`404`, favori toujours présent en base) — vérifié
- [x] Étudiant A peut toujours gérer ses propres favoris normalement — vérifié
- [x] Un compte non-étudiant (Admin/Bibliothécaire/Personne externe) reçoit `403` — vérifié (décision : strictement privé, pas d'accès de gestion)

### Décision
**✔️ VALIDÉE ET APPLIQUÉE** — `apps/favoris/serializers.py` (champ `etudiant` retiré de `FavoriCreateSerializer`) et `apps/favoris/views.py` (toutes les actions déduisent l'étudiant de `request.user.profil_etudiant`, `403` si absent, `404` si le favori ciblé n'appartient pas à l'appelant). Vérifié par tests unitaires (`apps/favoris/tests.py`) et par appel direct de l'API sur la base de dev (voir note sur le blocage de `manage.py test`, section 18/TECH-005).

---

## SEC-005 — IDOR / BOLA complet sur `Consultation` (apps/consultations)

**Catégorie :** Sécurité — Autorisation
**Gravité :** 🔴 Critique
**Statut :** ✔️ Terminée (ACT-006, 2026-09-20/21) — décision retenue : strictement privé, y compris pour Admin/Bibliothécaire (les stats agrégées `top-documents`/`top-recherches`, déjà `IsAdminUser`, restent inchangées). `terminer` (PATCH) a été inclus dans le correctif, il présentait la même faille sans avoir été listé dans le constat initial.
**Fichier :** `apps/consultations/views.py`
**Ligne :** 85-113, 254-263
**Endpoint :** `GET /api/consultations/`, `GET/DELETE /api/consultations/{id}/`, `GET /api/consultations/en-cours/`

### Constat
Même schéma que SEC-004 : `list` (filtre `user`), `retrieve`, `destroy` et `en_cours` (paramètre `user` **obligatoire**, en clair dans la doc Swagger) ne comparent jamais l'utilisateur ciblé à `request.user`. `vue`/`recherche` (POST) acceptent aussi un `user` optionnel dans le body, permettant d'enregistrer une consultation au nom de quelqu'un d'autre.

### Impact
Un utilisateur authentifié peut consulter l'historique de navigation et **les termes de recherche** (`recherche_query`, potentiellement révélateur du sujet de mémoire/recherche d'un étudiant) de n'importe quel autre utilisateur, et supprimer ses entrées d'historique. C'est une fuite de données comportementales, plus une atteinte à l'intégrité du journal (utile aussi pour les stats admin — un utilisateur malveillant pourrait fausser les statistiques `top-documents`/`top-recherches` en soumettant des vues/recherches au nom d'autrui).

### Cause
Identique à SEC-004 — absence de contrôle par objet, confiance dans un paramètre client.

### Solution proposée
- `vue`/`recherche` : toujours utiliser `request.user`, ignorer un éventuel `user` dans le payload (sauf appel interne/service à service, non applicable ici).
- `list`/`en-cours` : si `request.user` n'est ni Admin ni Bibliothécaire, forcer le filtre `user=request.user.id` et ignorer/rejeter toute tentative de cibler un autre utilisateur.
- `retrieve`/`destroy` : vérifier `consultation.user_id == request.user.id` (sauf rôle de gestion).

### Alternatives
Comme SEC-004 : séparer un endpoint "mon historique" (implicite) d'un endpoint de gestion admin explicite avec permission stricte.

### Risque de régression
Moyen — mêmes considérations que SEC-004 sur l'usage réel actuel du paramètre `user` par le frontend/l'app mobile.

### Tests nécessaires
- [x] Utilisateur A ne peut pas lire l'historique de B (`404`) — vérifié (`apps/consultations/tests.py`, `ConsultationIdorTests`)
- [x] Utilisateur A ne peut pas supprimer une consultation de B (`404`, consultation toujours présente) — vérifié
- [x] Utilisateur A ne peut pas terminer une consultation de B (`404`) — vérifié (ajouté au correctif)
- [x] Utilisateur A ne peut pas enregistrer une vue/recherche au nom de B (`user` envoyé ignoré, consultation attribuée à A) — vérifié
- [x] `en-cours` ne retourne que les consultations de l'appelant — vérifié
- [x] Un utilisateur peut toujours gérer ses propres consultations (lecture, clôture) — vérifié
- [x] Les stats `top-documents`/`top-recherches` (déjà `IsAdminUser`) restent fonctionnelles — non modifiées, hors périmètre

### Décision
**✔️ VALIDÉE ET APPLIQUÉE** — `apps/consultations/serializers.py` (champ `user` retiré de `ConsultationVueCreateSerializer`/`ConsultationRechercheCreateSerializer`) et `apps/consultations/views.py` (`list`/`en-cours` forcés sur `request.user`, `retrieve`/`destroy`/`terminer` vérifient la propriété, `vue`/`recherche` attribuent toujours à `request.user`). Vérifié par tests unitaires (`apps/consultations/tests.py`) et par appel direct de l'API sur la base de dev.

---

## SEC-006 — Contrôle d'accès vertical manquant sur les données de référence (Filière/Niveau/Spécialité/UE)

**Catégorie :** Sécurité — Autorisation
**Gravité :** 🔴 Critique
**Statut :** ✔️ Terminée (ACT-007, 2026-09-21) — décision retenue : Admin + Bibliothécaire autorisé (`peut_gerer_documents=true`), réutilisation de `CanManageDocuments`
**Fichier :** `apps/filiere/views.py:166`, `apps/niveau/views.py:125`, `apps/specialites/views.py:147`, `apps/ue/views.py:236,400`
**Endpoint :** `POST/PUT/PATCH/DELETE /api/filieres/`, `/api/niveaux/`, `/api/specialites/`, `/api/ues/` (+ détail par id)

### Constat
Ces quatre `ViewSet` déclarent `permission_classes = [IsAuthenticated]` **sans** `get_permissions()` pour restreindre `create`/`update`/`partial_update`/`destroy`. Comparé au pattern correctement appliqué ailleurs dans le même projet (`DocumentViewSet.get_permissions()` avec `CanManageDocuments`, ou le nouvel `AnneeAcademiqueViewSet.get_permissions()` avec `IsAdministrateur` ajouté cette session), ici **n'importe quel compte authentifié — y compris un étudiant** — peut créer, modifier ou supprimer une filière, un niveau, une spécialité ou une UE.

### Preuve
```python
# apps/filiere/views.py
class FiliereViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]   # <- s'applique à create/update/destroy aussi, pas seulement list/retrieve
```

### Impact
Un étudiant malveillant (ou un compte compromis) peut supprimer toutes les filières de l'université via `DELETE /api/filieres/{id}/`, cassant la navigation/le filtrage de tous les documents qui en dépendent (`Document.filiere` passe à `NULL` via `SET_NULL`), ou créer des données de référence invalides/polluantes. C'est une escalade de privilèges verticale directe.

### Cause
Oubli lors de la création de ces 4 apps — le pattern `get_permissions()` existe déjà ailleurs dans le projet mais n'a pas été repris ici.

### Solution proposée
Ajouter `get_permissions()` sur les 4 `ViewSet`, réservant `create`/`update`/`partial_update`/`destroy` à `IsAdministrateur` (le même que celui utilisé pour `AnneeAcademiqueViewSet`), en gardant `IsAuthenticated` seul pour `list`/`retrieve` (la lecture par un étudiant reste légitime, ex: peupler des filtres dans l'app mobile).

### Alternatives
Élargir à `IsAdminOrBibliothecaire` si les bibliothécaires doivent aussi pouvoir gérer ces données (à confirmer — pas clair actuellement qui doit avoir ce droit).

### Risque de régression
Faible à moyen : si un écran bibliothécaire utilise aujourd'hui ces endpoints en écriture, il faudra vérifier son rôle exact et adapter la permission choisie en conséquence plutôt que de bloquer un usage légitime.

### Tests nécessaires
- [x] Étudiant → 403 sur POST/DELETE filière/niveau/spécialité/UE — vérifié (tests + appel API direct)
- [x] Admin → toujours autorisé — vérifié
- [x] Bibliothécaire avec `peut_gerer_documents=true` → autorisé — vérifié (décision confirmée : Admin + Bibliothécaire)
- [x] `list`/`retrieve` restent accessibles à tout utilisateur authentifié — vérifié

### Décision
**✔️ VALIDÉE ET APPLIQUÉE** — `get_permissions()` ajouté sur les 5 ViewSets (`FiliereViewSet`, `NiveauViewSet`, `SpecialiteViewSet`, `UEViewSet`, et `ECUEViewSet` qui présentait la même faille sans avoir été listé dans le constat initial), réutilisant `CanManageDocuments` déjà existant dans `apps/documents/permissions.py`. Tests ajoutés dans `apps/filiere/tests.py`, `apps/niveau/tests.py`, `apps/specialites/tests.py`, `apps/ue/tests.py` ; vérifiés par appel direct de l'API sur la base de dev (`manage.py test` reste bloqué par TECH-005).

---

## SEC-007 — Absence de rate limiting sur les endpoints d'authentification

**Catégorie :** Sécurité — Authentification
**Gravité :** 🟠 Haute
**Statut :** ✔️ Terminée (2026-09-23) — décision retenue : throttling DRF intégré (pas de nouvelle dépendance)
**Fichier :** `core/settings.py` (`REST_FRAMEWORK`), `apps/users/services/auth_service.py`
**Endpoint :** `/api/auth/{etudiant,bibliothecaire,admin,personne-externe}/login/`, `/api/auth/*/totp/verify/`

### Constat
`REST_FRAMEWORK` ne définit aucun `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES`. Aucun paquet de type `django-axes` ou `django-ratelimit` n'est installé (absent de `requirements.txt`). Les messages d'erreur de connexion sont génériques et identiques en cas de mauvais matricule/email OU mauvais mot de passe (bon point, pas d'énumération par message), mais **rien n'empêche un nombre illimité de tentatives**.

### Impact
Attaque par force brute ou credential stuffing possible sans limite sur les mots de passe étudiants/bibliothécaires/admin, et sur les codes TOTP à 6 chiffres (`pyotp`) qui ont un espace de recherche restreint (10^6 possibilités, fenêtre de 30s) — un TOTP est nettement plus vulnérable au brute force qu'un mot de passe s'il n'y a aucun throttle sur `/totp/verify/`.

### Cause
Aucun mécanisme de limitation mis en place.

### Solution appliquée
`rest_framework.throttling.ScopedRateThrottle` avec `throttle_scope = 'login'`/`'totp'` ajouté sur les 12 vues de login + vérification TOTP (`apps/users/views/auth_views.py`) : étudiant, personne externe, bibliothécaire, admin, enseignant-chercheur, chercheur. Taux définis dans `core/settings.py` (`REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`) : `login: 5/min`, `totp: 5/min` — appliqués uniquement aux vues concernées, pas globalement à toute l'API.

### Alternatives
`django-axes` (verrouillage de compte après N échecs) — non retenu par le développeur pour rester sans nouvelle dépendance ; à reconsidérer si le throttling par IP s'avère insuffisant (ex: attaque distribuée sur plusieurs IP).

### Risque de régression
**Concrétisé et corrigé** : la première application a cassé 18 tests existants dans `apps/users` (`test_first_login_totp_api.py`, `test_personne_externe_api.py`, etc.) qui enchaînent plusieurs connexions en séquence — le cache de throttling (mémoire du process, `LocMemCache`) ne se réinitialise pas entre les méthodes de test d'une même exécution, donc les tentatives s'accumulent et finissent par dépasser 5/min en cours de suite. Corrigé en désactivant le throttle sous `manage.py test` (`RUNNING_TESTS = 'test' in sys.argv` dans `core/settings.py`, taux relevé à `10000/min` pendant les tests), avec un test dédié (`apps/users/test_rate_limiting_api.py`) qui patche directement `ScopedRateThrottle.THROTTLE_RATES` (nécessaire : DRF lit ce dict une seule fois à l'import du module, `@override_settings` sur `REST_FRAMEWORK` ne le met pas à jour dynamiquement) pour vérifier le vrai comportement (429 au-delà du seuil) sans perturber le reste de la suite.

### Tests nécessaires
- [x] Dépassement du seuil → 429 Too Many Requests — vérifié manuellement puis via test automatisé dédié (`LoginRateLimitingTests`, seuil patché à 3/min)
- [x] Connexion légitime toujours possible sous le seuil — vérifié
- [x] Suite de tests existante non perturbée — 18 échecs initiaux corrigés, suite complète repassée au vert (voir section 15/16)

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## SEC-008 — Upload de documents non validé (type, taille) + Content-Type reflété tel quel

**Catégorie :** Sécurité — Fichiers
**Gravité :** 🟠 Haute
**Statut :** ✔️ Terminée (2026-09-23) — décision retenue : PDF, Word (.doc/.docx), Images (jpg/png) autorisés ; PowerPoint exclu
**Fichier :** `apps/documents/serializers.py` (`DocumentCreateSerializer`, `DocumentUpdateSerializer`), `apps/documents/utils.py`, `apps/documents/views.py` (`fichier`, `ouvrir`)

### Constat
- Aucune liste blanche d'extensions/MIME types autorisés pour `file_path` (PDF/DOCX attendus implicitement, jamais vérifiés).
- Aucune taille maximale de fichier appliquée au niveau applicatif.
- `file_mime_type` peut être fourni explicitement par le client (`DocumentCreateSerializer.file_mime_type`, `required=False` mais pris tel quel s'il est fourni) et est ensuite renvoyé comme `Content-Type` HTTP par `fichier()` (`FileResponse(..., content_type=document.file_mime_type or DEFAULT_DOCUMENT_MIME_TYPE)`).

### Impact
Un compte disposant de `CanManageDocuments` (Admin/Bibliothécaire) — ou un tel compte compromis/hameçonné — peut téléverser un fichier `.html`/`.svg` avec un `file_mime_type` de son choix. Si un étudiant ouvre ensuite ce document via `GET /api/documents/{id}/ouvrir/` puis `GET .../fichier/` sans `?download=true`, le navigateur peut l'afficher inline avec le `Content-Type` fourni par l'attaquant → exécution de JavaScript dans le contexte de l'origine de l'app (XSS stocké), et vecteur de phishing interne. Le risque est limité par le fait qu'il faut déjà un compte de gestion documentaire, mais reste réel (compromission de compte bibliothécaire = pivot vers tous les étudiants).

### Cause
La validation actuelle (`DocumentCreateSerializer.validate`) vérifie la présence du fichier et la cohérence métier (filière/niveau/spécialité), mais pas son type ni sa taille.

### Solution appliquée
Nouvelle fonction `validate_document_upload()` dans `apps/documents/utils.py`, appelée dans `DocumentCreateSerializer.validate()` et `DocumentUpdateSerializer.validate()` (à chaque nouveau fichier) :
1. **Liste blanche** par extension : `.pdf`, `.doc`, `.docx`, `.jpg`/`.jpeg`, `.png` — rejette toute autre extension (dont `.pptx`, exclu par choix du développeur).
2. **Vérification de signature binaire** (magic bytes) sans nouvelle dépendance : `%PDF-` pour PDF, `\x89PNG\r\n\x1a\n` pour PNG, `\xff\xd8\xff` pour JPEG, `PK\x03\x04` (conteneur ZIP) pour DOCX, en-tête OLE (`\xd0\xcf\x11\xe0...`) pour DOC — détecte un fichier dont le contenu ne correspond pas à son extension (ex: HTML renommé en `.pdf`).
3. **Taille maximale** : 20 Mo (`MAX_DOCUMENT_UPLOAD_SIZE_BYTES`).
4. Le `file_mime_type` **n'est plus jamais pris du client** : toujours celui associé à l'extension validée côté serveur (`ALLOWED_DOCUMENT_UPLOAD_TYPES`). Le champ `file_mime_type` reste accepté en entrée pour compatibilité mais son `help_text` précise désormais qu'il est ignoré.

Point 3 de la proposition initiale (forcer `Content-Disposition: attachment` pour le non-PDF) **non appliqué** : avec la validation de contenu en place, les types autorisés restants (Word, images) ne présentent plus le risque XSS initial (HTML/SVG exclus de la liste blanche) ; forcer le téléchargement dégraderait l'aperçu des images sans bénéfice de sécurité supplémentaire proportionné.

### Résultat (vérifié)
```
PDF valide (signature %PDF- correcte)               -> 201
HTML renomme en .pdf (signature invalide)            -> 400 "contenu ne correspond pas a son extension"
.pptx (hors liste blanche)                           -> 400 "Type de fichier non autorise"
Fichier > 20 Mo                                      -> 400 "depasse la taille maximale autorisee"
PNG valide + file_mime_type client usurpe=text/html  -> 201, mime reellement stocke = image/png (client ignore)
```

### Alternatives
Servir les fichiers depuis un sous-domaine/origine séparée sans cookies/session partagés — défense en profondeur non retenue pour l'instant, la validation de contenu couvre déjà le vecteur identifié.

### Risque de régression
Les documents déjà uploadés avant ce correctif avec un type hors liste blanche (s'il en existe) restent en base et consultables normalement — la validation ne s'applique qu'aux nouveaux téléversements/remplacements de fichier, pas rétroactivement.

### Tests nécessaires
- [x] Upload PDF légitime toujours accepté — vérifié
- [x] Upload fichier au contenu usurpé rejeté — vérifié (HTML renommé `.pdf`)
- [x] Upload `.pptx` (hors liste blanche) rejeté — vérifié
- [x] Upload d'un fichier dépassant la taille max rejeté — vérifié
- [x] `Content-Type` stocké correspond au type réel détecté, pas à une valeur arbitraire du client — vérifié

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## SEC-009 — `ALLOWED_HOSTS` contient un domaine à confirmer

**Catégorie :** Configuration
**Gravité :** 🟡 Moyenne
**Statut :** 🔎 À discuter — **mis à jour le 2026-09-20** : `otl-bulkliquid.com` n'est pas un copier-coller accidentel, c'est un domaine réellement contrôlé par le développeur (identifiants email `it@otl-bulkliquid.com` confirmés fonctionnels, cf. SEC-003). Le constat initial ("aucun rapport avec le projet") est donc incorrect et retiré.
**Fichier :** `core/settings.py`
**Ligne :** 43-51

### Constat
```python
ALLOWED_HOSTS = [
    "otl-bulkliquid.com",
    "www.otl-bulkliquid.com",
    "127.0.0.1", "localhost", "10.0.2.2", "192.168.1.115", "192.168.1.27",
]
```
Le domaine est légitime, mais `ALLOWED_HOSTS` gouverne uniquement les en-têtes `Host` acceptés pour les requêtes HTTP de **l'application web** — c'est une question différente de « ce domaine sert à envoyer des emails ». Reste donc à confirmer : E-BIBLIO/PERED sera-t-il réellement servi sous `otl-bulkliquid.com`, ou est-ce un domaine réservé à un autre usage (ici, l'email) pendant que l'app web aura son propre nom de domaine à ajouter ici le moment venu ?

### Impact
Faible, informatif — pas un risque de sécurité en soi tant que la liste reste restrictive (elle l'est).

### Solution proposée
Confirmer avec le développeur le(s) domaine(s) réel(s) prévu(s) pour héberger l'application, et ajuster `ALLOWED_HOSTS` en conséquence le moment venu.

### Décision
**⏳ EN ATTENTE DE DISCUSSION** *(reclassée : simple clarification à faire, non plus une anomalie)*

---

## SEC-010 — Identifiants d'un autre projet en commentaire dans `settings.py`

**Catégorie :** Configuration
**Gravité :** 🟡 Moyenne
**Statut :** 🔎 À discuter
**Fichier :** `core/settings.py`
**Ligne :** 258-273

### Constat
Un bloc `DATABASES` MySQL entièrement commenté contient un nom de base, un utilisateur et **un mot de passe en clair** (`c2745157c_BIBLIOv1` / `#4h].2WrwNrELChB`) — probablement les identifiants cPanel réels d'un déploiement précédent ou d'un autre projet.

### Impact
Secret exposé dans un fichier tracké par Git, même si le code est inactif.

### Solution proposée
Supprimer entièrement ce bloc mort (le code actif utilise déjà PostgreSQL via `.env`). Si ces identifiants sont encore valides quelque part, les faire tourner aussi.

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

---

*(Le registre continuera avec SEC-011+ au fil des sessions suivantes si de nouveaux constats apparaissent — TECH-001 en section 18 couvre déjà l'observation MongoDB/PostgreSQL non transactionnel.)*

---

# 6. Registre des optimisations

## PERF-001 — Calcul de la taille totale des documents en boucle Python (I/O disque par fichier)

**Catégorie :** Performance
**Statut :** ✔️ Terminée (2026-09-23)
**Fichier :** `apps/documents/repositories.py`, `apps/documents/models/document.py`, migrations `0016`/`0017`
**Endpoint :** `GET /api/documents/stats/dashboard/`

### Problème
```python
@staticmethod
def get_storage_stats(...) -> dict[str, int]:
    queryset = DocumentRepository._apply_student_scope(
        Document.objects.only("id", "file_path"), ...
    )
    documents_count = queryset.count()
    documents_with_file_count = 0
    total_file_size = 0
    for document in queryset.iterator():
        file_size = document.file_size   # <- appelle self.file_path.size → stat() disque à chaque itération
        ...
        total_file_size += file_size
    ...
```

### Analyse actuelle
Chaque appel à `document.file_size` déclenche un appel système `stat()` sur le stockage de fichiers (`FieldFile.size`). Pour N documents, c'est N appels disque séquentiels en plus de la requête SQL initiale, exécutés à chaque chargement du tableau de bord admin. Avec quelques centaines de documents ça reste supportable, mais ça grandit linéairement et **sans plafond** avec la taille de la bibliothèque — et c'est en plus refait à chaque appel de l'endpoint (pas de cache).

### Requêtes SQL / I/O
**Avant :** 1 requête SQL (`SELECT id, file_path FROM documents ...`) + **N appels `stat()` disque** (N = nombre de documents visibles par l'utilisateur).

### Solution appliquée
`file_size` ajouté comme vrai champ (`BigIntegerField`, nullable) sur `Document`, en remplacement de l'ancienne `@property` du même nom (conflit de nom impossible sinon — une `@property` sans setter fait planter `setattr()` que Django utilise en interne). Calculé dans `Document.clean()` (donc à chaque `save()`, y compris lors d'un remplacement de fichier via l'endpoint de modification ajouté cette session — reste toujours synchronisé). Migration `0016` (ajout du champ) + `0017` (`RunPython`, backfill des documents déjà existants). `DocumentRepository.get_storage_stats()` utilise désormais `queryset.aggregate(Count(...), Sum("file_size"))` au lieu de la boucle Python.

### Résultat (vérifié)
```
Document.save() -> file_size stocke = 1008 octets (fichier de test de 1008 octets), sans requete supplementaire
get_storage_stats() -> 1 requete SQL (au lieu d'une boucle avec stat() disque par document)
```

### Effets secondaires possibles
`file_size` est une donnée dupliquée (source de vérité = le fichier) — reste synchronisée automatiquement à chaque `save()` grâce à `clean()`, y compris lors d'un remplacement de fichier.

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## PERF-002 — Recherche `icontains` multi-colonnes non indexée sur `Document`

**Catégorie :** Performance
**Statut :** 🔎 À discuter — reconfirmé le 2026-09-23 : toujours pas mesuré comme un problème réel, laissé de côté volontairement
**Fichier :** `apps/documents/repositories.py` (`get_filtered`)

### Problème
```python
if search:
    queryset = queryset.filter(
        Q(title__icontains=search)
        | Q(auteur__icontains=search)
        | Q(description__icontains=search)
        | Q(specialite__name__icontains=search)
        | Q(ue__code__icontains=search)
        | Q(ue__name__icontains=search)
    )
```

### Analyse actuelle
`icontains` (`LIKE '%...%'`) ne peut pas utiliser d'index B-tree standard sur PostgreSQL — chaque recherche texte fait un scan complet des colonnes concernées, sur plusieurs tables jointes en plus. Actuellement sans impact visible (peu de documents), mais c'est le genre de requête qui devient lente en premier quand le volume grossit (table de plusieurs milliers de documents).

### Optimisation proposée
Si la recherche devient un point chaud mesuré (pas avant), envisager une extension PostgreSQL `pg_trgm` + index `GIN` sur `title`/`description`, ou un champ de recherche dédié (`SearchVectorField` de Django). **Je ne recommande pas de le faire maintenant** tant que ce n'est pas mesuré comme un problème réel — ce serait de la sur-optimisation prématurée pour la taille actuelle du projet.

### Décision
**⏳ EN ATTENTE DE VALIDATION** *(faible priorité — à ne traiter que si mesuré comme lent)*

---

## PERF-003 — Aucune pagination ne fonctionne réellement sur les ViewSets du projet

**Catégorie :** Performance
**Statut :** ✔️ Partiellement appliquée (2026-09-23) — voir note ci-dessous sur la portée finale, réduite après vérification du frontend Angular
**Fichiers :** `apps/documents/views.py`, `apps/favoris/views.py`, `apps/consultations/views.py` (paginés) ; `apps/filiere/views.py`, `apps/niveau/views.py`, `apps/specialites/views.py`, `apps/ue/views.py` (×2), `apps/annee_academique/views.py` (**laissés tels quels**, voir note)
**Endpoint :** `GET /api/documents/`, `GET /api/favoris/favoris/`, `GET /api/consultations/consultations/`

### Note importante — portée réduite après vérification du frontend
Le projet est consommé par un frontend Angular (`digitalBiblioNew`, en dehors de ce dépôt). En lisant (lecture seule) `document-service.ts`, `filiere-service.ts` et `favori-service.ts`, ainsi que le composant `documents.ts`, j'ai constaté que :
- **`documents.ts`** et **`favori-service.ts`** gèrent déjà explicitement une réponse paginée DRF (`if (res.results !== undefined || res.count !== undefined) { ... }`) et envoient déjà `page`/`page_size` en paramètres — ils avaient donc été écrits en anticipant une pagination qui, côté backend, n'a jamais fonctionné. Activer la pagination ne casse rien ici, ça comble un écart déjà prévu côté front.
- **`filiere-service.ts`** en revanche ne gère **que** un tableau brut (`(Array.isArray(res) && Array.isArray(res[0])) ? res[0] : res`) — aucune gestion de `res.results`. Paginer `FiliereViewSet` aurait cassé l'affichage des filières côté Angular.
- `niveau`, `specialites`, `ue`, `annee_academique` côté Angular n'ont pas été vérifiés (le développeur a demandé de ne plus explorer le projet Angular après ce constat).

**Décision prise avec le développeur :** paginer uniquement `Documents`, `Favoris`, `Consultations` (dont le frontend gère déjà la forme paginée, et dont le volume grandit réellement dans le temps) ; laisser `Filière`/`Niveau`/`Spécialité`/`UE`/`ECUE`/`Année académique` inchangés (volume structurellement petit, et au moins un frontend connu n'est pas prêt à recevoir une réponse paginée pour ces ressources).

### Problème (constat initial, toujours valable pour les ViewSets non traités)
`core/settings.py` configure globalement :
```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
'PAGE_SIZE': 20,
```
Mais ce réglage global **ne s'applique jamais** automatiquement, car ces `ViewSet` héritent tous de `viewsets.ViewSet` (pas `GenericViewSet`/`ModelViewSet`), et leurs méthodes `list()` construisaient la réponse à la main sans jamais appeler `self.paginate_queryset()`/`self.get_paginated_response()`.

### Problème
`core/settings.py` configure globalement :
```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
'PAGE_SIZE': 20,
```
Mais ce réglage global **ne s'applique jamais**, car les 8 `ViewSet` du projet héritent tous de `viewsets.ViewSet` (pas `GenericViewSet`/`ModelViewSet`), et leurs méthodes `list()` construisent la réponse à la main :
```python
# pattern identique dans les 8 fichiers
def list(self, request):
    qs = _service.list_xxx(...)
    return Response(XxxSerializer(qs, many=True).data)
```
La pagination DRF n'est déclenchée que par les mixins génériques (`self.paginate_queryset()` + `self.get_paginated_response()`), jamais automatiquement par un simple `Response(...)`. `DocumentViewSet` va même jusqu'à déclarer explicitement `pagination_class = None` (ligne 424) — un réglage inerte ici puisque la pagination n'était de toute façon jamais invoquée, mais qui traduit une fausse impression de contrôle.

### Analyse actuelle
Concrètement, `GET /api/documents/` (ou n'importe quelle autre liste) renvoie **tous** les enregistrements correspondant aux filtres en une seule réponse JSON, sans `LIMIT`, quel que soit leur nombre. C'est sans impact visible aujourd'hui (peu de documents), mais c'est le point qui dégradera le plus vite l'app à mesure que la bibliothèque grossit :
- **Documents** : la ressource la plus volumineuse et la plus consultée (recherche, filtres) — impact le plus fort.
- **Consultations** : chaque vue/recherche crée une ligne — historique d'un utilisateur actif qui grossit sans borne dans le temps.
- **Favoris** : borné par étudiant (scope corrigé par SEC-004), volume naturellement plus faible mais pas nul.
- **Filière/Niveau/Spécialité/UE/ECUE/Année académique** : données de référence, volume structurellement petit — impact faible mais même bug.

Effet côté app mobile Flutter : chaque écran de liste télécharge l'intégralité des résultats avant de pouvoir en afficher un seul, au lieu de charger par page — payload réseau et temps de premier affichage qui grandissent avec la base, sans qu'aucun réglage actuel (y compris `PAGE_SIZE`) n'y change quoi que ce soit.

### Solution appliquée
Nouvelle classe partagée `core/pagination.py` :
```python
from rest_framework.pagination import PageNumberPagination

class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'   # deja envoye par le front Angular
    max_page_size = 200
```
Appliquée à `DocumentViewSet`, `FavoriViewSet`, `ConsultationViewSet` : ajout de `pagination_class = StandardResultsPagination` et, dans chaque `list()`, remplacement de `return Response(Serializer(qs, many=True).data)` par :
```python
paginator = self.pagination_class()
page = paginator.paginate_queryset(qs, request, view=self)
return paginator.get_paginated_response(Serializer(page, many=True).data)
```
Pagination manuelle explicite (pas de changement de classe de base `viewsets.ViewSet`), même pattern que `EtudiantListView` (`apps/users`) qui paginait déjà manuellement.

### Résultat (vérifié)
```
GET /api/documents/                  -> {count, next, previous, results} (avant : tableau brut illimité)
GET /api/documents/?page_size=5      -> count: 20, results: 5 éléments
GET /api/favoris/favoris/            -> {count, next, previous, results}
GET /api/consultations/consultations/ -> {count, next, previous, results}
GET /api/filieres/filieres/          -> toujours un tableau brut (inchangé, comme prévu)
```

### Effets secondaires possibles
Changement de forme de réponse JSON pour Documents/Favoris/Consultations (`{"count", "next", "previous", "results"}` au lieu d'un tableau brut) — compatible avec le frontend Angular actuel qui gère déjà cette forme pour ces 3 ressources (vérifié). L'app Flutter mobile (encore en construction) devra en tenir compte le moment venu si elle consomme ces mêmes endpoints.

### Décision
**✔️ VALIDÉE ET APPLIQUÉE (portée réduite à Documents/Favoris/Consultations)** — Filière/Niveau/Spécialité/UE/ECUE/Année académique restent en `⏳ À discuter` si une pagination y est un jour souhaitée, après vérification de leurs consommateurs Angular respectifs.

---

## PERF-004 — `SpecialiteSerializer` : 3 requêtes `.count()` par spécialité affichée

**Catégorie :** Performance
**Statut :** ✔️ Terminée (2026-09-23)
**Fichiers :** `apps/specialites/models.py:91-105`, `apps/specialites/serializers.py:21-24`, `apps/specialites/repositories.py:10-37`
**Endpoint :** `GET /api/specialites/`

### Problème
```python
# apps/specialites/models.py
@property
def nb_etudiants(self):
    return self.etudiants.count()

@property
def nb_documents(self):
    return self.documents.count()

@property
def nb_ues(self):
    return self.ues.count()
```
Ces 3 `@property` sont lues par `SpecialiteSerializer` pour chaque spécialité sérialisée, et aucune n'est annotée sur le queryset (`SpecialiteRepository.get_all()` ne fait que `select_related("niveau__filiere")`).

### Analyse actuelle
**Avant :** pour une liste de 30 spécialités, 1 requête pour la liste + 30 × 3 = 90 requêtes `COUNT` supplémentaires = **91 requêtes** au lieu d'1 seule possible. Le nombre de requêtes grandit linéairement avec le nombre de spécialités (endpoint utilisé pour peupler des filtres/menus, potentiellement appelé souvent par le mobile).

### Optimisation proposée
```python
# apps/specialites/repositories.py
from django.db.models import Count

@staticmethod
def get_all() -> QuerySet:
    return Specialite.objects.select_related("niveau__filiere").annotate(
        nb_etudiants=Count("etudiants", distinct=True),
        nb_documents=Count("documents", distinct=True),
        nb_ues=Count("ues", distinct=True),
    )
```
**Note d'implémentation :** annoter directement `nb_etudiants`/`nb_documents`/`nb_ues` (mêmes noms que les `@property`) aurait provoqué une erreur au chargement (`AttributeError: can't set attribute`), Django appelant `setattr()` sur l'instance pour poser la valeur annotée, ce qui heurte une `@property` sans setter. Utilisé le même contournement déjà en place dans le projet (`_nb_documents` sur `TypeDocumentSerializer`) : annotation préfixée `_nb_etudiants`/`_nb_documents`/`_nb_ues`, et la `@property` vérifie `hasattr(self, '_nb_etudiants')` avant de recalculer.

### Résultat (vérifié)
```
PERF-004: 22 specialites serialisees en 1 requete (au lieu de ~66 avant le correctif)
```
Appliqué à `get_all()`, `get_by_id()`, `get_by_niveau()` et `search()` dans `apps/specialites/repositories.py`, pour couvrir tous les points d'entrée qui alimentent `SpecialiteSerializer`.

### Effets secondaires possibles
Aucun constaté — les valeurs annotées (`distinct=True` sur chaque `Count`) correspondent exactement aux valeurs `.count()` d'origine.

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## PERF-005 — `UESerializer.coef_total` : l'agrégat contourne le `prefetch_related` existant

**Catégorie :** Performance
**Statut :** ✔️ Terminée (2026-09-23)
**Fichiers :** `apps/ue/models.py:43-50`, `apps/ue/repositories.py:16-17`
**Endpoint :** `GET /api/ues/`

### Problème
```python
# apps/ue/models.py
@property
def coef_total(self) -> Decimal:
    if not self.pk:
        return self.coef or Decimal("0.00")
    total = self.ecues.aggregate(total=Sum("coef"))["total"]
    return total or Decimal("0.00")
```
`UERepository.get_all()` fait bien `prefetch_related("specialites", "ecues")`, mais appeler `.aggregate()` sur une relation déjà préchargée déclenche **quand même** une nouvelle requête SQL — Django n'utilise le cache du `prefetch_related` que pour `.all()`/itération directe, jamais pour `.aggregate()` ou `.filter()`.

### Analyse actuelle
**Avant :** pour une liste de 50 UE : 1 (liste) + 1 (prefetch specialites) + 1 (prefetch ecues) + 50 requêtes `SUM` supplémentaires (une par UE, via `coef_total` lu par le serializer) = **53 requêtes** au lieu de 3. Le `prefetch_related` existant devient inefficace pour ce champ précis — un correctif partiel qui masque le vrai problème.

### Optimisation proposée
```python
@property
def coef_total(self) -> Decimal:
    if not self.pk:
        return self.coef or Decimal("0.00")
    # reutilise le cache prefetch_related au lieu de re-interroger la DB
    return sum((e.coef for e in self.ecues.all()), Decimal("0.00"))
```
`self.ecues.all()` sans filtre supplémentaire réutilise bien le cache du `prefetch_related`. Alternative plus robuste si on veut éviter tout calcul Python : annoter `Coalesce(Sum("ecues__coef"), Decimal("0.00"))` directement dans `UERepository.get_all()`.

### Résultat attendu
**Après :** 3 requêtes (liste + 2 prefetch) au lieu de 53, pour une liste de 50 UE.

**Gain attendu :** réduction proportionnelle au nombre d'UE affichées. Non mesuré (dépend du volume actuel), mais le nombre de requêtes est vérifiable directement.

### Effets secondaires possibles
Le calcul Python (`sum()` sur les ECUE en mémoire) donne exactement le même résultat que l'agrégat SQL tant que le prefetch n'est pas filtré. L'import `Sum` (devenu inutilisé) a été retiré de `apps/ue/models.py`.

### Résultat (vérifié)
```
PERF-005: coef_total = 4.00 (2 ECUE à 2.50 et 1.50) en 3 requêtes (liste + prefetch specialites + prefetch ecues) — 0 requête SUM supplémentaire
```

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## PERF-006 — Export Excel des étudiants : `derniere_reactivation_par` non préchargé

**Catégorie :** Performance
**Statut :** ✔️ Terminée (2026-09-23)
**Fichiers :** `apps/users/repositories/etudiant_repository.py` (`get_all`), `apps/users/services/etudiant_export_service.py:196, 230-232`
**Endpoint :** Export Excel des étudiants (`EtudiantExportExcelView`)

### Problème
`EtudiantRepository.get_all()` fait `select_related('user', 'filiere', 'niveau', 'specialite')` mais **pas** `'derniere_reactivation_par'` (alors que `get_by_id()`, utilisé pour le détail d'un seul étudiant, l'inclut déjà). `EtudiantExcelExportService._row_from_etudiant` accède pourtant à `etudiant.derniere_reactivation_par` pour chaque ligne exportée.

### Analyse actuelle
**Avant :** pour chaque étudiant qui a déjà été réactivé au moins une fois (champ non `NULL`), une requête SQL séparée est déclenchée pour charger l'admin/bibliothécaire ayant fait la réactivation. Sur un export de 500 étudiants dont 300 ont déjà été réactivés, ça fait **jusqu'à 300 requêtes supplémentaires** pour un seul export Excel.

### Optimisation proposée
```python
# apps/users/repositories/etudiant_repository.py
@staticmethod
def get_all(filters: dict = None) -> QuerySet:
    qs = Etudiant.objects.select_related(
        'user', 'filiere', 'niveau', 'specialite', 'derniere_reactivation_par'
    ).all()
    ...
```

### Résultat attendu
**Après :** 1 requête (avec les `JOIN` nécessaires) au lieu de jusqu'à 301 pour un export de 500 étudiants.

**Gain attendu :** proportionnel au nombre d'étudiants déjà réactivés dans l'export — non mesuré, dépend du volume réel de réactivations, mais le principe (1 JOIN au lieu de N requêtes) est direct et sans ambiguïté.

### Effets secondaires possibles
Aucun — ajout pur d'un `select_related`, ne change aucun comportement, juste le nombre de requêtes.

### Résultat (vérifié)
`EtudiantRepository.get_all().query.select_related` confirme `derniere_reactivation_par` maintenant inclus aux côtés de `user`/`filiere`/`niveau`/`specialite`.

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

---

## PERF-007 — `BibliothecaireListView` : seule liste de `apps/users` sans pagination

**Catégorie :** Performance
**Statut :** ✔️ Terminée (2026-09-23)
**Fichier :** `apps/users/views/creation_views.py:1118-1126`
**Endpoint :** `GET /api/bibliothecaires/`

### Problème
```python
class BibliothecaireListView(APIView):
    def get(self, request):
        qs         = BibliothecaireRepository.get_all()
        serializer = BibliothecaireDetailSerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'results': serializer.data})
```
Contrairement aux autres listes de `apps/users` (`EtudiantListView`, `PersonneExterneListView`, `EnseignantChercheurListView`, `ChercheurListView`), qui paginent déjà manuellement (page/page_size + slicing), celle-ci renvoie l'intégralité du queryset en une fois. Ce n'est pas du N+1 (le `select_related('user')` est correct), juste une incohérence avec le reste de l'app.

### Analyse actuelle
Impact plus faible que PERF-003/004/005/006 car le nombre de comptes bibliothécaires est structurellement plus petit que celui des étudiants ou des documents — mais même principe que PERF-003, localisé sur un seul endpoint déjà identifié précisément.

### Optimisation appliquée
Réutilisé le même pattern de pagination manuelle (page/page_size + slicing) déjà en place dans `EtudiantListView`/`PersonneExterneListView` du même fichier — cohérence de style, pas de nouvelle dépendance.

**Note :** contrairement à PERF-003 (Documents/Favoris/Consultations), ce n'est **pas** un changement de forme de réponse — l'endpoint renvoyait déjà un objet `{success, count, results}` (jamais un tableau brut). Le changement ajoute juste `page`/`pages` et limite `results` à une page au lieu de tout renvoyer — répercussion possible : si un écran Angular affichait déjà tous les bibliothécaires sans pagination visible, il n'en affichera plus que 20 par défaut tant que ses contrôles de pagination (s'ils existent) ne sont pas branchés sur `page`/`page_size`. Non vérifié côté Angular (hors périmètre demandé).

### Résultat (vérifié)
```
GET /api/bibliothecaires/ -> {success, count, page, pages, results} (page=1, pages=1, count=3 sur l'environnement de dev)
```

### Décision
**✔️ VALIDÉE ET APPLIQUÉE**

### Décision
**⏳ EN ATTENTE DE VALIDATION**

---

# 7. Audit des permissions

| ID       | Endpoint                         | Auth | Permission déclarée | Contrôle par objet | Risque |
| -------- | --------------------------------- | :--: | -------------------- | :-----------------: | :----: |
| AUTH-001 | `/api/favoris/*`                  | ✅   | `IsAuthenticated`    | ❌                   | 🔴 (SEC-004) |
| AUTH-002 | `/api/consultations/*`            | ✅   | `IsAuthenticated` (+ `IsAdminUser` sur les stats top) | ❌ sauf stats | 🔴 (SEC-005) |
| AUTH-003 | `/api/filieres/*` écriture        | ✅   | `IsAuthenticated`    | N/A (vertical, pas horizontal) | 🔴 (SEC-006) |
| AUTH-004 | `/api/niveaux/*`, `/api/specialites/*`, `/api/ues/*` écriture | ✅ | `IsAuthenticated` | N/A | 🔴 (SEC-006) |
| AUTH-005 | `/api/documents/*` écriture       | ✅   | `IsAuthenticated` + `CanManageDocuments` | ✅ (rôle vérifié) | 🟢 |
| AUTH-006 | `/api/documents/*` lecture (étudiant) | ✅ | `IsAuthenticated` | ✅ (scope filière/niveau/spécialité appliqué dans `DocumentService._get_student_document_scope`) | 🟢 |
| AUTH-007 | `/api/annees-academiques/*` écriture (ajouté cette session) | ✅ | `IsAuthenticated` + `IsAdministrateur` | ✅ | 🟢 |
| AUTH-008 | `/api/etudiants/`, `/api/bibliothecaires/`, etc. (création) | ✅ | `IsAdministrateur` / `IsAdminOrBibliothecaire` | ✅ | 🟢 |

### Points à vérifier
- [x] Authentification — JWT correctement exigé partout (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated` par défaut)
- [x] Permissions globales — cohérentes pour `documents`, `users`, `annee_academique`
- [ ] Permissions par objet — **manquantes sur `favoris` et `consultations`** (SEC-004, SEC-005)
- [ ] Séparation des rôles en écriture sur les données de référence — **manquante** (SEC-006)
- [ ] Accès horizontal (utilisateur → utilisateur) — **failles confirmées** (SEC-004, SEC-005)
- [x] Accès vertical sur `documents`/`users` — correctement cloisonné
- [ ] Accès vertical sur `filiere`/`niveau`/`specialites`/`ue` — **faille confirmée** (SEC-006)
- [ ] Modification/suppression d'une ressource appartenant à un autre utilisateur — **possible sur favoris/consultations**

---

# 8. Audit base de données

## Models

| Model            | Relations principales | Index explicites | Contraintes | Risques | Optimisation |
| ----------------- | --------------------- | ----------------- | ----------- | ------- | -------------- |
| `Document`        | FK → Filiere/Niveau/Specialite/ECUE/User (tous `SET_NULL`) | Aucun explicite hors PK/FK auto | — | Recherche `icontains` non indexée (PERF-002) ; `file_size` recalculé à chaque lecture (PERF-001) | Ajouter `db_index=True` sur `type`, ou composite selon les filtres les plus fréquents, si mesuré nécessaire |
| `Consultation`    | FK → User/Document (`SET_NULL`) | `['user','created_at']`, `['document','created_at']`, `['type_consultation']` | — | Bien indexé | RAS |
| `Favori`          | FK → Etudiant/Document (`CASCADE`) | Aucun explicite | `unique_together=(etudiant, document)` ✅ | RAS côté DB (le problème est applicatif, SEC-004) | — |
| `Etudiant`        | FK → User(1-1)/Filiere/Niveau/Specialite | Aucun explicite | `matricule` unique | RAS | — |
| `AnneeAcademique` (ajouté) | Aucune FK | Aucun explicite | — | Table petite (quelques lignes/an), pas de besoin d'index | RAS |

### Requêtes problématiques

| ID     | Endpoint                          | Problème                          | Requêtes (approx.) | Solution            |
| ------ | ---------------------------------- | ----------------------------------- | -------------------: | -------------------- |
| DB-001 | `GET /api/documents/stats/dashboard/` | Boucle Python + `stat()` disque par document | 1 SQL + N I/O disque | Voir PERF-001 |
| DB-002 | `GET /api/documents/` (liste)      | `select_related` déjà appliqué (`type, filiere, niveau, specialite, ue, ajoute_par`) + `annotate(Count(...))` pour favoris/consultations — **correctement optimisé**, pas de N+1 détecté | 1 requête | Aucune action nécessaire |

### Vérifications
- [x] N+1 — non détecté sur `DocumentRepository.get_all()` (bon usage de `select_related`/`annotate`)
- [ ] N+1 — non vérifié en détail sur `apps/users` (listes étudiants/bibliothécaires) — à approfondir si tu veux que j'aille plus loin
- [ ] Index manquants — voir tableau ci-dessus (faible priorité tant que non mesuré)
- [x] Contraintes uniques — présentes où pertinent (`Filiere.name`, `Etudiant.matricule`, `Favori` unique_together, `UE.code`)
- [x] Foreign keys — cohérentes, `SET_NULL`/`CASCADE` utilisés de façon appropriée selon le sens métier
- [ ] Transactions explicites — peu utilisées (`transaction.atomic()` seulement dans le nouveau `AnneeAcademique.save()`) ; la création d'étudiant (`creer_etudiant`) fait plusieurs écritures (`User`, `Etudiant`, TOTP) **sans transaction englobante** — voir TECH-002
- [ ] Race conditions — non testées spécifiquement (ex: deux requêtes simultanées de `toggle` favori pourraient théoriquement violer `unique_together` si mal gérées — le `unique_together` protège au niveau DB, donc pas de doublon possible, mais pas de test de concurrence écrit)
- [x] `bulk_create`/`bulk_update` — non utilisés actuellement, mais volumes actuels ne le justifient pas encore

---

# 9. Audit authentification

### JWT
- [x] Access token — 15 min par défaut (configurable via `JWT_ACCESS_MINUTES`), raisonnable
- [x] Refresh token — 7 jours par défaut, rotation activée (`ROTATE_REFRESH_TOKENS=True`)
- [x] Expiration — configurée
- [x] Rotation — activée
- [x] Révocation — `BLACKLIST_AFTER_ROTATION=True` + `rest_framework_simplejwt.token_blacklist` installé
- [ ] Stockage côté client (mobile Flutter) — non vérifiable à ce stade (app pas encore assez avancée dans `mobile/`)
- [x] Blacklist — app installée et utilisée
- [ ] HTTPS forcé — aucun `SECURE_SSL_REDIRECT` trouvé dans `settings.py` (à vérifier/ajouter avant mise en production cPanel)
- [ ] Rate limiting — **absent** (SEC-007)

### Mot de passe
- [x] Hash sécurisé — Django `AbstractUser` par défaut (PBKDF2), pas de hash custom dangereux détecté
- [x] Politique de mot de passe — `AUTH_PASSWORD_VALIDATORS` standard Django + `validate_password()` appelé explicitement à la création (`EtudiantCreateSerializer.validate`)
- [ ] Reset password — flux `OTP Email` présent (`Auth — OTP Email` dans les tags Swagger) mais non audité en détail dans cette passe
- [ ] Brute force — **non protégé** (SEC-007)
- [x] Énumération utilisateur — messages d'erreur de login génériques et identiques (bon point)

---

# 10. Audit uploads et fichiers

- [ ] Validation extension — **absente** (SEC-008)
- [ ] Validation MIME réelle (signature de fichier) — **absente**, seul le `Content-Type` déclaré par le client est utilisé
- [ ] Taille maximale — **absente** au niveau du serializer/modèle (seule une capacité de stockage *globale* existe via `DocumentStorageConfiguration`)
- [x] Nom de fichier — `Path(...).name` utilisé pour éviter l'injection de chemin dans le nom stocké en base
- [ ] Path traversal sur l'upload lui-même — le nom de fichier physique est reconstruit via `document_upload_path` (slugify des segments) plutôt que de réutiliser le nom brut du client → **protégé**
- [ ] Fichiers exécutables — **non bloqués** (SEC-008)
- [x] Stockage privé — les fichiers sont servis via une vue authentifiée (`fichier`/`ouvrir`), pas exposés directement sous `/media/` sans passer par Django (à confirmer côté configuration serveur web de prod, qui n'expose pas `MEDIA_ROOT` directement)
- [ ] Contrôle d'accès au fichier — le scope étudiant (filière/niveau/spécialité) s'applique à `get_document()`, donc `fichier()`/`ouvrir()` en héritent correctement ✅
- [x] Suppression sécurisée — soft-delete via `safedelete`, le fichier physique n'est pas supprimé du disque à la suppression logique (à confirmer si c'est voulu ou si ça laisse des fichiers orphelins — TECH-003)

---

# 11. Audit configuration

| Élément         | État | Observation |
| ---------------- | :--: | ------------ |
| `DEBUG`          | 🔴   | Forcé à `True` en dur (SEC-002) |
| `SECRET_KEY`     | 🔴   | Correctement lue via `.env`/`decouple`, mais le `.env` est commité (SEC-001) |
| `ALLOWED_HOSTS`  | 🟡   | Contient un domaine d'un autre projet (SEC-009) |
| CORS             | 🟡   | `CORS_ALLOWED_ORIGINS` restreint à une liste explicite (bon point) mais inclut `salam-logistics.com`, un domaine sans rapport apparent avec E-BIBLIO — à confirmer si volontaire |
| CSRF             | 🟢   | `CSRF_TRUSTED_ORIGINS` défini ; API en JWT (pas de session), donc CSRF peu pertinent pour l'API elle-même, reste pertinent pour `/admin/` |
| HTTPS            | ⬜   | Aucun `SECURE_SSL_REDIRECT` trouvé — à définir avant mise en production |
| HSTS             | ⬜   | Non configuré |
| CSP              | ⬜   | Non configuré (pas de paquet `django-csp`) |
| Cookies          | 🟡   | `SESSION_COOKIE_SECURE = False` explicitement — pertinent surtout pour `/admin/` Django (session-based) ; à passer à `True` en production HTTPS |
| Secrets dans Git | 🔴   | `.env` tracké + secrets en dur dans `settings.py` (SEC-001, SEC-003, SEC-010) |
| Logs             | 🟡   | Journal applicatif via MongoDB (`apps.history`) pour les actions métier ; pas de configuration `LOGGING` Django explicite trouvée dans `settings.py` (les erreurs serveur ne semblent pas centralisées/loguées en fichier) |

---

# 12. Plan d'action

Les actions sont proposées par ordre de priorité. **Aucune n'est exécutée sans ta validation explicite (`VALIDER`)** — je les traite une par une, dans l'ordre que tu choisis.

| ID      | Action                                                              | Priorité | Statut       | Validation |
| ------- | -------------------------------------------------------------------- | :------: | ------------ | :--------: |
| ACT-001 | Rotation des secrets (mot de passe PostgreSQL, MongoDB Atlas, `SECRET_KEY`) — **hors code, à faire par toi** | 🔴 | ⏳ Discussion | ❌ |
| ACT-002 | Retirer `.env` du suivi Git + créer `.gitignore`                    | 🔴       | ✔️ Terminée   | ✅         |
| ACT-003 | Supprimer `DEBUG=True` en dur (SEC-002)                              | 🔴       | ✔️ Terminée   | ✅         |
| ACT-004 | Déplacer les identifiants SMTP vers `.env` (SEC-003)                 | 🔴       | ✔️ Terminée   | ✅ *(fait via un changement de fournisseur SMTP, cf. SEC-003)* |
| ACT-005 | Corriger l'IDOR sur `Favori` (SEC-004)                               | 🔴       | ✔️ Terminée   | ✅         |
| ACT-006 | Corriger l'IDOR sur `Consultation` (SEC-005)                         | 🔴       | ✔️ Terminée   | ✅         |
| ACT-007 | Restreindre l'écriture sur Filière/Niveau/Spécialité/UE/ECUE (SEC-006) | 🔴 | ✔️ Terminée | ✅ |
| ACT-008 | Ajouter le rate limiting sur les endpoints d'auth (SEC-007)          | 🟠       | ✔️ Terminée   | ✅         |
| ACT-009 | Valider type/taille des fichiers uploadés (SEC-008)                  | 🟠       | ✔️ Terminée   | ✅         |
| ACT-010 | Nettoyer `ALLOWED_HOSTS` et le bloc DB mort (SEC-010)                 | 🟡       | ⏳ Discussion | ❌         |
| ACT-011 | Stocker `file_size` en base + agrégation SQL (PERF-001)              | 🟡       | ✔️ Terminée   | ✅         |
| ACT-012 | Corriger la migration MySQL→Postgres qui bloque `manage.py test` (TECH-005) | 🟠 | ⏳ Discussion | ❌ |
| ACT-013 | Corriger le préfixe d'URL doublé sur Filière/Niveau/Spécialité/UE/Favoris/Consultations (TECH-006) | 🟠 | ⏳ Discussion | ❌ |
| ACT-014 | Faire fonctionner la pagination sur Documents/Favoris/Consultations (PERF-003, portée réduite) | 🟠 | ✔️ Terminée | ✅ |
| ACT-015 | Annoter `nb_etudiants`/`nb_documents`/`nb_ues` sur le queryset Spécialités (PERF-004) | 🟠 | ✔️ Terminée | ✅ |
| ACT-016 | Corriger `UESerializer.coef_total` pour réutiliser le cache prefetch (PERF-005) | 🟠 | ✔️ Terminée | ✅ |
| ACT-017 | Ajouter `select_related('derniere_reactivation_par')` à l'export Excel étudiants (PERF-006) | 🟡 | ✔️ Terminée | ✅ |
| ACT-018 | Paginer `BibliothecaireListView` comme les autres listes de `apps/users` (PERF-007) | 🟢 | ✔️ Terminée | ✅ |

---

# 13. Cycle obligatoire pour chaque action

```text
AUDIT → IDENTIFICATION → EXPLICATION → PROPOSITION → DISCUSSION
  → VALIDATION UTILISATEUR → MODIFICATION → TEST → MESURE
  → VALIDATION FINALE → MISE À JOUR DU RAPPORT
```

**Aucune modification avant validation explicite.**

---

# 14. Fiche d'une action

*(Modèle réutilisé pour chaque ACT-XXX au moment où on le traite — rempli en section 14 bis au fur et à mesure, pas à l'avance pour ne pas dupliquer les registres 5/6 avant discussion.)*

---

# 15. Journal des modifications

| Date | Action | Fichiers | Modification | Tests | Résultat |
| ---------- | ------- | -------- | ------------- | ----- | -------- |
| 2026-09-20 | ACT-003 | `core/settings.py` | Suppression de la ligne `DEBUG=True` codée en dur (ligne 355) | `manage.py check` | ✅ |
| 2026-09-20 | ACT-002 | `.gitignore` (créé), `.env.example` (créé), `.env`/`.history/`/`__pycache__` (168 fichiers)/`staticfiles/` (276 fichiers) retirés de l'index Git | `git rm --cached` sur les 4 cibles, fichiers conservés sur disque, rien commité | `git status`, `manage.py check` | ✅ |
| 2026-09-20 | ACT-004 | `core/settings.py`, `.env`, `.env.example` | Config email lue depuis `.env` (`EMAIL_HOST/PORT/USE_SSL/HOST_USER/HOST_PASSWORD`), fournisseur changé pour un compte SMTP cPanel dédié (port 465, SSL implicite) au lieu du Gmail personnel en dur | `manage.py check`, `manage.py sendtestemail` | ✅ (confirmé par le développeur) |
| 2026-09-21 | ACT-005 | `apps/favoris/serializers.py` (champ `etudiant` retiré de `FavoriCreateSerializer`), `apps/favoris/views.py` (toutes les actions scopées sur `request.user.profil_etudiant`), `apps/favoris/tests.py` (créé, 6 tests) | IDOR corrigé : chaque étudiant ne peut plus lire/créer/supprimer que ses propres favoris | `manage.py check`, appel direct API sur la base de dev (voir TECH-005 — `manage.py test` bloqué par un bug de migration préexistant, sans rapport) | ✅ |
| 2026-09-21 | ACT-006 | `apps/consultations/serializers.py` (champ `user` retiré des 2 serializers de création), `apps/consultations/views.py` (`list`/`en-cours`/`retrieve`/`destroy`/`terminer`/`vue`/`recherche` scopés sur `request.user`), `apps/consultations/tests.py` (créé, 7 tests) | IDOR corrigé : chaque utilisateur ne peut plus lire/créer/supprimer/clôturer que ses propres consultations | `manage.py check`, appel direct API sur la base de dev | ✅ |
| 2026-09-21 | ACT-007 | `apps/filiere/views.py`, `apps/niveau/views.py`, `apps/specialites/views.py`, `apps/ue/views.py` (5 ViewSets : `get_permissions()` ajouté, réutilise `CanManageDocuments`), `apps/filiere/tests.py`, `apps/niveau/tests.py`, `apps/specialites/tests.py`, `apps/ue/tests.py` (tests ajoutés) | Écriture (create/update/partial_update/destroy) réservée à Admin + Bibliothécaire autorisé ; lecture restée ouverte à tout utilisateur authentifié | `manage.py check`, appel direct API sur la base de dev (Étudiant → 403, Bibliothécaire autorisé → 201, Admin → 204) | ✅ |
| 2026-09-23 | ACT-014 | `core/pagination.py` (créé), `apps/documents/views.py`, `apps/favoris/views.py`, `apps/consultations/views.py` (`pagination_class` + `list()` paginés) | Pagination DRF réelle activée sur Documents/Favoris/Consultations (`{count, next, previous, results}`) ; Filière/Niveau/Spécialité/UE/ECUE/Année académique volontairement laissés inchangés après vérification du frontend Angular (`filiere-service.ts` n'aurait pas géré la forme paginée) | `manage.py check`, appel direct API sur la base de dev (forme de réponse + `?page_size=`) | ✅ |
| 2026-09-23 | ACT-015 | `apps/specialites/repositories.py` (`_with_counts()`, annotations `_nb_etudiants`/`_nb_documents`/`_nb_ues` sur `get_all`/`get_by_id`/`get_by_niveau`/`search`), `apps/specialites/models.py` (les 3 `@property` lisent l'annotation si présente) | 22 spécialités sérialisées en 1 requête au lieu de ~66 | `manage.py check`, comptage réel des requêtes (`connection.queries`) | ✅ |
| 2026-09-23 | ACT-016 | `apps/ue/models.py` (`coef_total` utilise `self.ecues.all()` au lieu de `.aggregate()`, import `Sum` retiré) | `coef_total` réutilise le cache `prefetch_related`, 0 requête SUM supplémentaire par UE | `manage.py check`, comptage réel des requêtes + valeur `coef_total` vérifiée (4.00 pour 2.50+1.50) | ✅ |
| 2026-09-23 | ACT-017 | `apps/users/repositories/etudiant_repository.py` (`get_all()` : ajout `'derniere_reactivation_par'` au `select_related`) | Export Excel étudiants : jusqu'à 300 requêtes en moins sur 500 étudiants déjà réactivés | `manage.py check`, inspection de `qs.query.select_related` | ✅ |
| 2026-09-23 | ACT-018 | `apps/users/views/creation_views.py` (`BibliothecaireListView.get()` paginé, pattern identique à `EtudiantListView`) | Réponse désormais `{success, count, page, pages, results}` (limitée par page) au lieu de tout renvoyer | `manage.py check`, appel direct API sur la base de dev | ✅ |
| 2026-09-23 | ACT-008 | `apps/users/views/auth_views.py` (`throttle_classes`/`throttle_scope` sur 12 vues login/TOTP), `core/settings.py` (`DEFAULT_THROTTLE_RATES`) | Rate limiting 5/min sur login et vérification TOTP pour les 6 rôles | `manage.py check`, test réel (5× 400 puis 429 à la 6e tentative) | ✅ |
| 2026-09-23 | ACT-009 | `apps/documents/utils.py` (`validate_document_upload()`, liste blanche + signatures binaires + taille max), `apps/documents/serializers.py` (branché sur `DocumentCreateSerializer`/`DocumentUpdateSerializer`, `file_mime_type` client ignoré) | Upload restreint à PDF/Word/Images avec vérification de contenu réel, 20 Mo max | `manage.py check`, 5 scénarios testés (PDF valide, contenu usurpé, extension refusée, taille excessive, mime client ignoré) | ✅ |
| 2026-09-23 | ACT-011 | `apps/documents/models/document.py` (champ `file_size` remplace la `@property`, calculé dans `clean()`), migrations `0016`/`0017` (ajout + backfill), `apps/documents/repositories.py` (`get_storage_stats()` en `aggregate()`) | Stats de stockage en 1 requête SQL au lieu d'un `stat()` disque par document | `manage.py check`, migrations appliquées, comptage réel des requêtes | ✅ |
| 2026-09-23 | TECH-004 | `core/settings.py` (`LOGGING`, fichier `logs/django.log` avec rotation) | Erreurs serveur (`django.request`) et sécurité (`django.security`) désormais capturées dans un fichier, même quand `DEBUG=False` | `manage.py check`, log d'erreur réel écrit et relu dans le fichier | ✅ |
| 2026-09-23 | TECH-005 | `apps/documents/migrations/0012_...` (SQL corrigé en syntaxe PostgreSQL, en place — pas de nouvelle migration, une tentative initiale avec une migration en aval s'est avérée inefficace et a été abandonnée) | `manage.py test` fonctionne enfin sur une base fraîche | `manage.py test apps.filiere` (5 tests OK), puis suite complète (voir ci-dessous) |  ✅ |
| 2026-09-23 | (suite TECH-005) | `core/settings.py` (`RUNNING_TESTS`, throttle désactivé sous test), `apps/users/test_rate_limiting_api.py` (créé), `apps/favoris/tests.py` + `apps/consultations/tests.py` (2 assertions corrigées pour lire `response.data["results"]` après pagination PERF-003, 1 comparaison UUID/str corrigée) | `manage.py test` débloqué a révélé 18 échecs préexistants non détectés (interaction SEC-007/suite de tests, et tests écrits avant l'activation de PERF-003) — tous corrigés | `manage.py test apps.favoris apps.consultations apps.filiere apps.niveau apps.specialites apps.ue` : 31/31 | ✅ |
| 2026-09-23 | (suite TECH-005, apps.documents) | `apps/documents/tests.py` : 5 assertions adaptées à la pagination PERF-003 (`response.data["results"]`), 3 contenus de fichier factices préfixés `%PDF-` (SEC-008 rejetait les anciens, sans signature réelle), 1 test authentifié en admin plutôt qu'étudiant (bug de fixture préexistant sans rapport, révélé par le déblocage de `manage.py test` — cf. constat ci-dessous) | `manage.py test apps.documents` : 31/31 | `manage.py test apps.documents` | ✅ |

# 16. Tests de non-régression

| Test                                  | Avant | Après | Résultat |
| --------------------------------------- | :---: | :---: | :------: |
| Authentification (4 rôles + TOTP)      | ✅    | —     | à rejouer après chaque action touchant `auth_service.py` |
| Étudiant A ne peut pas lire favoris de B | ❌   | ✅    | vérifié (`FavoriIdorTests`, ACT-005) |
| Étudiant A ne peut pas créer/supprimer un favori de B | ❌ | ✅ | vérifié (`FavoriIdorTests`, ACT-005) |
| Étudiant A ne peut pas lire historique de B | ❌ | ✅   | vérifié (`ConsultationIdorTests`, ACT-006) |
| Étudiant A ne peut pas supprimer/clôturer une consultation de B | ❌ | ✅ | vérifié (`ConsultationIdorTests`, ACT-006) |
| Étudiant ne peut pas supprimer une filière | ❌ | —    | à écrire (SEC-006, pas encore traité) |
| Upload document PDF légitime            | ✅    | —     | à revérifier après SEC-008 |

---

# 17. Mesures de performance

| Endpoint                              | Avant | Après | Méthode de mesure |
| --------------------------------------- | ----: | ----: | ------------------- |
| `GET /api/documents/stats/dashboard/`  | non mesuré (dépend du nombre de documents actuels) | — | à mesurer avec `django.db.connection.queries` + `time.perf_counter()` avant/après PERF-001 |

*Aucun gain de performance n'est affirmé sans mesure — les chiffres ci-dessus seront renseignés une fois PERF-001 validé et implémenté.*

---

# 18. Dette technique

| ID       | Problème                                                        | Impact | Priorité | Décision   |
| -------- | ------------------------------------------------------------------ | ------ | :------: | ---------- |
| TECH-001 | Écritures MongoDB (`apps.history`) non transactionnelles avec PostgreSQL | Incohérence possible entre l'état métier et le journal d'audit en cas d'échec partiel | 🟢 | À discuter |
| TECH-002 | `EtudiantCreationService.creer_etudiant` effectue plusieurs écritures (`User`, `Etudiant`, secret TOTP) sans `transaction.atomic()` englobante | Un échec à mi-parcours peut laisser un `User` créé sans profil `Etudiant` complet | 🟡 | À discuter |
| TECH-003 | Suppression logique (`safedelete`) d'un `Document` ne supprime pas le fichier physique associé | Accumulation de fichiers orphelins sur le disque au fil du temps | 🟢 | À discuter |
| TECH-004 | ✔️ **Résolu le 2026-09-23.** Absence de configuration `LOGGING` Django explicite | `LOGGING` ajouté dans `core/settings.py` : fichier `logs/django.log` avec rotation (5 Mo × 5), erreurs serveur (`django.request`) et sécurité (`django.security`) capturées à partir du niveau `ERROR`/`WARNING`, plus sortie console. Vérifié par un log d'erreur réel écrit dans le fichier. `logs/` déjà couvert par `.gitignore` (`*.log`). | 🟠 | ✔️ Terminée |
| TECH-005 | ✔️ **Résolu le 2026-09-23.** `apps/documents/migrations/0012_...` utilisait du SQL MySQL (`MODIFY COLUMN`), incompatible PostgreSQL, bloquant toute base fraîche. | **Tentative initiale ratée** : ajouter une migration corrective *après* la 0012 ne fonctionne pas, car Django rejoue les migrations dans l'ordre et 0012 plante avant même d'atteindre le correctif — leçon retenue. **Correctif réel** : la migration 0012 elle-même a été corrigée en place (`ALTER COLUMN ... TYPE varchar(1024)`, syntaxe PostgreSQL) — sûr car Django ne rejoue jamais une migration déjà marquée appliquée sur une base existante ; seule une base neuve (test, nouvel environnement) rejoue réellement son contenu. Vérifié : `manage.py test` crée maintenant une base fraîche et exécute les tests avec succès (31/31 sur les apps de cette session, favoris/consultations/filiere/niveau/specialites/ue). Une migration 0018 ajoutée par erreur dans la première tentative a été laissée en place (inoffensive, ré-applique la même largeur de colonne). | 🟠 | ✔️ Terminée |
| TECH-006 | **Portée corrigée le 2026-09-21** — ne touche pas que Favoris/Consultations : `apps/filiere`, `apps/niveau`, `apps/specialites` et `apps/ue` ont le même bug (leur router ré-enregistre son propre préfixe alors que `core/urls.py` le monte déjà sous le même préfixe). Endpoints réels confirmés via le schéma OpenAPI : `/api/filieres/filieres/...`, `/api/niveaux/niveaux/...`, `/api/specialites/specialites/...`, `/api/ues/ues/...`, `/api/ues/ecues/...`, `/api/favoris/favoris/...`, `/api/consultations/consultations/...`. Seuls `apps/documents` (préfixe vide déliberé) et `apps/annee_academique` (monté sur `api/` nu) suivent le pattern correct `/api/<ressource>/...`. Cette découverte a d'ailleurs faussé ma première vérification manuelle de SEC-006 (testée par erreur sur `/api/filieres/` au lieu de `/api/filieres/filieres/`, ce qui a montré des `403`/`404` inattendus avant correction). Non corrigé — à voir avec toi si l'app Flutter cible déjà ces URLs doublées (auquel cas les corriger casserait le client existant) avant de changer quoi que ce soit. Priorité relevée vu l'ampleur réelle. | 🟠 | À discuter |
| TECH-007 | **Découvert le 2026-09-23** — `apps/users/admin.py` (`api_historique`, `api_stats`) lit encore le journal d'actions depuis une collection **MongoDB** (`core/mongo_client.py`, collection `historique_actions`), alors que les écritures actuelles passent par `HistoriqueActionService.log()` vers le modèle SQL `HistoriqueAction` (PostgreSQL). Ces deux vues admin lisent donc probablement une collection Mongo qui n'est plus alimentée par le code actuel (code mort/legacy, ou double-écriture à vérifier). Pas un problème de performance ORM — à vérifier séparément si ces vues admin sont encore utilisées avant de décider quoi en faire (supprimer, ou faire pointer vers le modèle SQL). | 🟡 | À discuter |
| TECH-008 | ✔️ **Résolu le 2026-09-23.** Bug de fixture préexistant, sans rapport avec cette session, révélé uniquement par le déblocage de TECH-005 : `test_list_type_documents_returns_existing_types` (`apps/documents/tests.py`) s'authentifiait en étudiant pour vérifier `GET /api/documents/types/`, mais `TypeDocumentViewSet.get_queryset()` filtre automatiquement par niveau pour les étudiants — et les types créés dans `setUp()` ne sont liés à aucun niveau, donc la liste retournée à un étudiant est toujours vide. | Test corrigé pour s'authentifier en admin (pas concerné par ce filtre) — le test vérifie une capacité générale, pas ce filtrage spécifique (déjà couvert par d'autres tests). Aucun changement de comportement applicatif. | 🟢 | ✔️ Terminée |

---

# 19. État final (mis à jour le 2026-09-21)

## Sécurité (mis à jour le 2026-09-23)
- 🔴 Critique : 1 restante — SEC-001 partiellement traitée (rotation des secrets PostgreSQL/MongoDB/`SECRET_KEY` toujours en attente côté développeur, hors code). SEC-002 à SEC-006 toutes résolues.
- 🟠 Haute : 3 restantes — TECH-004 (logging absent), TECH-005 (migration MySQL bloquant `manage.py test`), TECH-006 (préfixe d'URL doublé, désormais compris comme le comportement attendu par le front Angular plutôt qu'un bug à corriger). SEC-007 et SEC-008 résolues.
- 🟡 Moyenne : 1 (SEC-010 ; SEC-009 reclassée en simple clarification)
- 🟢 Faible : 2

## Performance (mis à jour le 2026-09-23)
- Optimisations identifiées : 7 (PERF-001 à PERF-007)
- Optimisations validées : 6 (toutes sauf PERF-002)
- Optimisations réalisées : 6 — reste PERF-002 (recherche non indexée), volontairement laissée de côté (non mesurée comme un problème réel)

## API
- Endpoints analysés en détail : 14 (échantillon)
- Endpoints nécessitant une correction confirmée : 0 (SEC-004, SEC-005, SEC-006 tous corrigés — restent les points hors-sécurité TECH-005/TECH-006)

## Tests
- Tests existants avant l'audit : présents sur `apps/users` (TOTP, profil, export Excel, règles de spécialité), `apps/documents`, `apps/specialites`, `apps/ue`
- Tests ajoutés pendant cet audit : 28 (`apps/favoris` : 6 ; `apps/consultations` : 7 ; `apps/filiere` : 5 ; `apps/niveau` : 3 ; `apps/specialites` : 3 ; `apps/ue` : 3 ; `apps/users/test_rate_limiting_api.py` : 2)
- Tests réussis / échoués : **102/102 (suite complète du projet, `manage.py test apps`)** — TECH-005 corrigé le 2026-09-23 a débloqué `manage.py test`, ce qui a révélé et permis de corriger 18 échecs liés à SEC-007/PERF-003, 8 échecs liés à PERF-003/SEC-008 dans `apps/documents`, 1 bug de fixture préexistant (TECH-008) et 1 fichier de test entièrement obsolète supprimé (`apps/users/tests.py`, testait une architecture d'auth remplacée depuis longtemps)

---

# 20. Historique des décisions

| ID      | Date       | Sujet | Décision |
| ------- | ---------- | ----- | -------- |
| DEC-000 | 2026-09-20 | Audit initial réalisé, aucune modification appliquée | Rapport livré, en attente de tes retours par ACT-XXX |
| DEC-001 | 2026-09-20 | ACT-002 (retrait `.env`/`.history`/`__pycache__`/`staticfiles` du suivi Git + `.gitignore`) et ACT-003 (`DEBUG=True` en dur) | Validée ("VALIDE LES DEUX") et appliquée |
| DEC-002 | 2026-09-20 | ACT-004 (config SMTP) : passage à un compte cPanel dédié plutôt que rotation du mot de passe Gmail | Validée implicitement (paramètres fournis par le développeur) et appliquée, testée fonctionnelle |
| DEC-003 | 2026-09-20 | SEC-009 (`ALLOWED_HOSTS` / `otl-bulkliquid.com`) | Constat initial corrigé : domaine confirmé légitime, reclassé en clarification à faire plutôt qu'anomalie |
| DEC-004 | 2026-09-21 | Portée de ACT-005/ACT-006 (Favoris/Consultations accessibles à l'Admin/Bibliothécaire ou strictement privés) | Tranchée : strictement privé pour tout le monde, y compris Admin/Bibliothécaire |
| DEC-005 | 2026-09-21 | ACT-005 (IDOR Favoris) et ACT-006 (IDOR Consultations, `terminer` inclus) | Validée ("je valide") et appliquée, vérifiée par 13 tests (voir section 15/16) |
| DEC-006 | 2026-09-21 | Portée de ACT-007 (SEC-006) : Admin seul ou Admin + Bibliothécaire pour gérer Filière/Niveau/Spécialité/UE | Tranchée : Admin + Bibliothécaire autorisé (`peut_gerer_documents=true`), réutilisation de `CanManageDocuments` |
| DEC-007 | 2026-09-21 | Blocage local `core/__init__.py` (import pymysql) + `.env` (`DB_*` commentés) | Résolus directement par le développeur (pymysql commenté localement, `DB_*` décommentés) — confirmé "en prod j'utilise MySQL", donc aucune modification de `core/__init__.py` par Claude |
| DEC-008 | 2026-09-21 | ACT-007 (SEC-006, 5 ViewSets) | Validée et appliquée, vérifiée par 5 tests par app (26 au total avec ACT-005/006) |
| DEC-009 | 2026-09-21 | TECH-006 : portée corrigée, touche aussi Filière/Niveau/Spécialité/UE (pas seulement Favoris/Consultations) | Priorité relevée de 🟡 à 🟠, toujours en attente de décision (ACT-013) |
| DEC-006 | 2026-09-21 | TECH-005 (migration MySQL bloquant `manage.py test`) et TECH-006 (préfixe d'URL doublé Favoris/Consultations) | Découverts pendant la vérification d'ACT-005/006, non corrigés — en attente de ta décision (ACT-012, ACT-013) |
| DEC-010 | 2026-09-23 | Audit performance demandé (endpoints/requêtes) — sous-traité en partie à un agent d'exploration en arrière-plan pour `apps/users`, `niveau`, `specialites`, `ue`, `history`, `annee_academique` | 4 nouveaux N+1/incohérences confirmés (PERF-004 à PERF-007), ajoutés au registre avec fiches complètes |
| DEC-011 | 2026-09-23 | Confirmation : l'API est aussi consommée par un frontend Angular (`digitalBiblioNew`, hors de ce dépôt), pas seulement l'app Flutter mobile | Lecture (seule) de 3 services Angular pour évaluer le risque de casse avant d'activer PERF-003 |
| DEC-012 | 2026-09-23 | Portée de PERF-003 (pagination) : tout paginer au risque de casser le front Angular des données de référence, ou réduire la portée | Tranchée : ne paginer que Documents/Favoris/Consultations (déjà gérés côté Angular) ; Filière/Niveau/Spécialité/UE/ECUE/Année académique laissés inchangés. Le développeur a explicitement demandé de ne plus modifier ni explorer le projet Angular — uniquement le backend. Validée et appliquée. |
| DEC-013 | 2026-09-23 | ACT-015 (N+1 Spécialités), ACT-016 (coef_total UE), ACT-017 (export Excel étudiants), ACT-018 (pagination Bibliothécaires) | Validées ("On continue dessus") et appliquées, vérifiées individuellement (comptage de requêtes réel pour ACT-015/016, inspection directe pour ACT-017/018) |
| DEC-014 | 2026-09-23 | SEC-007 : throttling DRF intégré vs `django-axes` | Tranchée : throttling DRF (pas de nouvelle dépendance) |
| DEC-015 | 2026-09-23 | SEC-008 : quels types de fichiers rester autorisés à l'upload | Tranchée : PDF, Word (.doc/.docx), Images (jpg/png) — PowerPoint explicitement exclu |
| DEC-016 | 2026-09-23 | ACT-008 (rate limiting), ACT-009 (validation upload), ACT-011 (stats stockage, avec migration + backfill) | Validées ("SEC-007/SEC-008 ... PERF-001/PERF-002") et appliquées, vérifiées individuellement. PERF-002 reconfirmé laissé de côté (faible priorité, non mesuré). |
| DEC-017 | 2026-09-23 | TECH-004 (destination des logs) | Tranchée : fichier local avec rotation, adapté à cPanel |
| DEC-018 | 2026-09-23 | TECH-005 (migration corrective) | Validée ("Oui, vas-y") — tentative initiale (migration en aval) ratée et documentée, correctif réel appliqué en éditant la migration 0012 en place |
| DEC-019 | 2026-09-23 | TECH-008 (bug de fixture préexistant `test_list_type_documents_returns_existing_types`, révélé par le déblocage de `manage.py test`) | Tranchée : corriger le test plutôt que le laisser de côté |
| DEC-020 | 2026-09-23 | `apps/users/tests.py` (fichier entier testant une architecture d'auth remplacée, `ImportError` au chargement — `StudentRegistrationSerializer` n'existe plus nulle part) | Validée ("Oui, supprime-le") et supprimé |
| DEC-021 | 2026-09-23 | Suite complète du projet (`manage.py test apps`) | **102/102 tests passent.** Confirmation finale après la cascade de corrections déclenchée par TECH-005 (18 + 8 + 1 échecs corrigés, 1 fichier obsolète supprimé). |
