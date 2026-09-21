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
**Statut :** 🔎 À discuter
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
- [ ] Étudiant A ne peut pas lister les favoris de B
- [ ] Étudiant A ne peut pas créer un favori pour B
- [ ] Étudiant A ne peut pas supprimer un favori de B
- [ ] Étudiant A peut toujours gérer ses propres favoris normalement
- [ ] Admin/Bibliothécaire (si le besoin est confirmé) garde l'accès nécessaire

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

---

## SEC-005 — IDOR / BOLA complet sur `Consultation` (apps/consultations)

**Catégorie :** Sécurité — Autorisation
**Gravité :** 🔴 Critique
**Statut :** 🔎 À discuter
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
- [ ] Utilisateur A ne peut pas lire l'historique de B
- [ ] Utilisateur A ne peut pas supprimer une consultation de B
- [ ] Utilisateur A ne peut pas enregistrer une vue/recherche au nom de B
- [ ] Les stats `top-documents`/`top-recherches` (déjà `IsAdminUser`, correctement gardées) restent fonctionnelles

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

---

## SEC-006 — Contrôle d'accès vertical manquant sur les données de référence (Filière/Niveau/Spécialité/UE)

**Catégorie :** Sécurité — Autorisation
**Gravité :** 🔴 Critique
**Statut :** 🔎 À discuter
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
- [ ] Étudiant → 403 sur POST/PUT/PATCH/DELETE filière/niveau/spécialité/UE
- [ ] Admin → toujours autorisé
- [ ] Bibliothécaire → comportement à définir avec toi puis testé en conséquence
- [ ] `list`/`retrieve` restent accessibles à tout utilisateur authentifié

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

---

## SEC-007 — Absence de rate limiting sur les endpoints d'authentification

**Catégorie :** Sécurité — Authentification
**Gravité :** 🟠 Haute
**Statut :** 🔎 À discuter
**Fichier :** `core/settings.py` (`REST_FRAMEWORK`), `apps/users/services/auth_service.py`
**Endpoint :** `/api/auth/{etudiant,bibliothecaire,admin,personne-externe}/login/`, `/api/auth/*/totp/verify/`

### Constat
`REST_FRAMEWORK` ne définit aucun `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES`. Aucun paquet de type `django-axes` ou `django-ratelimit` n'est installé (absent de `requirements.txt`). Les messages d'erreur de connexion sont génériques et identiques en cas de mauvais matricule/email OU mauvais mot de passe (bon point, pas d'énumération par message), mais **rien n'empêche un nombre illimité de tentatives**.

### Impact
Attaque par force brute ou credential stuffing possible sans limite sur les mots de passe étudiants/bibliothécaires/admin, et sur les codes TOTP à 6 chiffres (`pyotp`) qui ont un espace de recherche restreint (10^6 possibilités, fenêtre de 30s) — un TOTP est nettement plus vulnérable au brute force qu'un mot de passe s'il n'y a aucun throttle sur `/totp/verify/`.

### Cause
Aucun mécanisme de limitation mis en place.

### Solution proposée
Ajouter `rest_framework.throttling.ScopedRateThrottle` (ou équivalent) sur les vues de login et de vérification TOTP, avec une limite basse (ex: 5 tentatives / minute / IP), et envisager `django-axes` pour un verrouillage de compte après N échecs.

### Alternatives
Rate limiting au niveau serveur web (Nginx/Apache sur cPanel) plutôt que dans Django — complémentaire mais pas suffisant seul si l'app est aussi accédée via l'IP interne d'un reverse proxy partagé.

### Risque de régression
Faible — ajout additif, ne change pas le comportement pour un usage normal.

### Tests nécessaires
- [ ] Dépassement du seuil → 429 Too Many Requests
- [ ] Connexion légitime toujours possible sous le seuil

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

---

## SEC-008 — Upload de documents non validé (type, taille) + Content-Type reflété tel quel

**Catégorie :** Sécurité — Fichiers
**Gravité :** 🟠 Haute
**Statut :** 🔎 À discuter
**Fichier :** `apps/documents/serializers.py` (`DocumentCreateSerializer`), `apps/documents/utils.py`, `apps/documents/views.py` (`fichier`, `ouvrir`)

### Constat
- Aucune liste blanche d'extensions/MIME types autorisés pour `file_path` (PDF/DOCX attendus implicitement, jamais vérifiés).
- Aucune taille maximale de fichier appliquée au niveau applicatif.
- `file_mime_type` peut être fourni explicitement par le client (`DocumentCreateSerializer.file_mime_type`, `required=False` mais pris tel quel s'il est fourni) et est ensuite renvoyé comme `Content-Type` HTTP par `fichier()` (`FileResponse(..., content_type=document.file_mime_type or DEFAULT_DOCUMENT_MIME_TYPE)`).

### Impact
Un compte disposant de `CanManageDocuments` (Admin/Bibliothécaire) — ou un tel compte compromis/hameçonné — peut téléverser un fichier `.html`/`.svg` avec un `file_mime_type` de son choix. Si un étudiant ouvre ensuite ce document via `GET /api/documents/{id}/ouvrir/` puis `GET .../fichier/` sans `?download=true`, le navigateur peut l'afficher inline avec le `Content-Type` fourni par l'attaquant → exécution de JavaScript dans le contexte de l'origine de l'app (XSS stocké), et vecteur de phishing interne. Le risque est limité par le fait qu'il faut déjà un compte de gestion documentaire, mais reste réel (compromission de compte bibliothécaire = pivot vers tous les étudiants).

### Cause
La validation actuelle (`DocumentCreateSerializer.validate`) vérifie la présence du fichier et la cohérence métier (filière/niveau/spécialité), mais pas son type ni sa taille.

### Solution proposée
1. Restreindre `file_mime_type`/l'extension à une liste blanche (PDF, DOCX, PPTX, images courantes...) déterminée côté serveur à partir du contenu réel du fichier (pas seulement l'en-tête `Content-Type` envoyé par le client) — idéalement via une détection de signature (`python-magic` ou équivalent).
2. Ajouter une taille maximale (`DocumentStorageConfiguration` existe déjà pour la capacité globale — un plafond par fichier serait complémentaire).
3. Forcer `as_attachment=True` (ou au minimum `Content-Disposition: attachment`) pour tout type de fichier qui n'est pas un PDF, pour empêcher le rendu inline dans le navigateur.

### Alternatives
Servir les fichiers depuis un sous-domaine/origine séparée sans cookies/session partagés, pour neutraliser l'impact d'un éventuel XSS stocké (défense en profondeur, plus lourd à mettre en place).

### Risque de régression
Faible à moyen — dépend des types de fichiers réellement utilisés aujourd'hui en production ; à confirmer avec toi avant de figer la liste blanche.

### Tests nécessaires
- [ ] Upload PDF légitime toujours accepté
- [ ] Upload `.html`/`.exe`/`.php` rejeté
- [ ] Upload d'un fichier dépassant la taille max rejeté
- [ ] `Content-Type` renvoyé par `/fichier/` correspond au type réel détecté, pas à une valeur arbitraire du client

### Décision
**⏳ EN ATTENTE DE DISCUSSION**

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
**Statut :** 🔎 À discuter
**Fichier :** `apps/documents/repositories.py`
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

### Optimisation proposée
Stocker la taille du fichier en base au moment de l'upload (nouveau champ `file_size` sur `Document`, rempli dans `clean()`/`save()` une seule fois), puis utiliser `queryset.aggregate(total=Sum("file_size"))` — une seule requête SQL, zéro appel disque au moment de la lecture des stats.

```python
# Après (illustratif, à discuter avant implémentation)
stats = queryset.aggregate(
    documents_count=Count("id"),
    total_file_size=Sum("file_size"),
)
```

### Résultat attendu
**Après :** 1 requête SQL agrégée, 0 appel disque à la lecture des stats.

**Gain attendu :** suppression de l'I/O disque proportionnelle au nombre de documents sur un endpoint de dashboard potentiellement appelé souvent. Gain non mesuré à ce stade (pas encore de volumétrie de production) — à confirmer par un chronométrage avant/après une fois la bibliothèque plus fournie.

### Effets secondaires possibles
Nécessite une migration (nouveau champ) + un script de backfill pour les documents déjà existants (calculer `file_size` une fois pour toutes les lignes actuelles). Le champ devient une donnée dupliquée (source de vérité = le fichier) qu'il faudra garder synchronisée si un fichier est remplacé (déjà le cas avec l'endpoint de modification de document ajouté cette session — à revoir ensemble à ce moment-là).

### Décision
**⏳ EN ATTENTE DE VALIDATION**

---

## PERF-002 — Recherche `icontains` multi-colonnes non indexée sur `Document`

**Catégorie :** Performance
**Statut :** 🔎 À discuter
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
| ACT-005 | Corriger l'IDOR sur `Favori` (SEC-004)                               | 🔴       | ⏳ Discussion | ❌         |
| ACT-006 | Corriger l'IDOR sur `Consultation` (SEC-005)                         | 🔴       | ⏳ Discussion | ❌         |
| ACT-007 | Restreindre l'écriture sur Filière/Niveau/Spécialité/UE à l'Admin (SEC-006) | 🔴 | ⏳ Discussion | ❌     |
| ACT-008 | Ajouter le rate limiting sur les endpoints d'auth (SEC-007)          | 🟠       | ⏳ Discussion | ❌         |
| ACT-009 | Valider type/taille des fichiers uploadés (SEC-008)                  | 🟠       | ⏳ Discussion | ❌         |
| ACT-010 | Nettoyer `ALLOWED_HOSTS` et le bloc DB mort (SEC-009, SEC-010)        | 🟡       | ⏳ Discussion | ❌         |
| ACT-011 | Stocker `file_size` en base + agrégation SQL (PERF-001)              | 🟡       | ⏳ Discussion | ❌         |

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

---

# 16. Tests de non-régression

| Test                                  | Avant | Après | Résultat |
| --------------------------------------- | :---: | :---: | :------: |
| Authentification (4 rôles + TOTP)      | ✅    | —     | à rejouer après chaque action touchant `auth_service.py` |
| Étudiant A ne peut pas lire favoris de B | ❌   | —     | à écrire (SEC-004) |
| Étudiant A ne peut pas lire historique de B | ❌ | —    | à écrire (SEC-005) |
| Étudiant ne peut pas supprimer une filière | ❌ | —    | à écrire (SEC-006) |
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
| TECH-004 | Absence de configuration `LOGGING` Django explicite | Erreurs serveur potentiellement invisibles une fois `DEBUG=False` corrigé (SEC-002) — sans logging fichier/externe, les 500 en prod ne laissent aucune trace consultable | 🟠 | À discuter (dépend de ACT-003) |

---

# 19. État final (au moment de cet audit initial)

## Sécurité (mis à jour le 2026-09-20)
- 🔴 Critique : 4 restantes (SEC-004, SEC-005, SEC-006 non traitées ; SEC-001 partiellement traitée) — SEC-002 et SEC-003 résolues
- 🟠 Haute : 3 (inchangé — SEC-007, SEC-008, et la note TECH-004 associée)
- 🟡 Moyenne : 3 (SEC-010 inchangée ; SEC-009 reclassée en simple clarification, non plus une anomalie)
- 🟢 Faible : 2

## Performance
- Optimisations identifiées : 2
- Optimisations validées : 0
- Optimisations réalisées : 0

## API
- Endpoints analysés en détail : 14 (échantillon)
- Endpoints nécessitant une correction confirmée : 9 (favoris, consultations, filière/niveau/spécialité/UE en écriture)

## Tests
- Tests existants : présents sur `apps/users` (TOTP, profil, export Excel, règles de spécialité)
- Tests ajoutés pendant cet audit : 0 (aucun test automatisé ajouté — les vérifications faites étaient manuelles : `manage.py check`, `sendtestemail`)
- Tests réussis / échoués : 3/3 vérifications manuelles réussies (ACT-002, ACT-003, ACT-004)

---

# 20. Historique des décisions

| ID      | Date       | Sujet | Décision |
| ------- | ---------- | ----- | -------- |
| DEC-000 | 2026-09-20 | Audit initial réalisé, aucune modification appliquée | Rapport livré, en attente de tes retours par ACT-XXX |
| DEC-001 | 2026-09-20 | ACT-002 (retrait `.env`/`.history`/`__pycache__`/`staticfiles` du suivi Git + `.gitignore`) et ACT-003 (`DEBUG=True` en dur) | Validée ("VALIDE LES DEUX") et appliquée |
| DEC-002 | 2026-09-20 | ACT-004 (config SMTP) : passage à un compte cPanel dédié plutôt que rotation du mot de passe Gmail | Validée implicitement (paramètres fournis par le développeur) et appliquée, testée fonctionnelle |
| DEC-003 | 2026-09-20 | SEC-009 (`ALLOWED_HOSTS` / `otl-bulkliquid.com`) | Constat initial corrigé : domaine confirmé légitime, reclassé en clarification à faire plutôt qu'anomalie |
