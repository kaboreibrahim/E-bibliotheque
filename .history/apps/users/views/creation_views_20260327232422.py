
"""
=============================================================================
 apps/users/views/creation_views.py
 APIViews — Création Étudiant (Biblio/Admin) + Création Bibliothécaire (Admin)
=============================================================================
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser

from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
)
from rest_framework import serializers as s

from apps.users.serializers.creation_serializers import (
    EtudiantCreateSerializer,
    EtudiantUpdateSerializer,
    EtudiantActiverSerializer,
    EtudiantDetailSerializer,
    BibliothecaireCreateSerializer,
    BibliothecaireUpdateSerializer,
    BibliothecaireDetailSerializer,
)
from apps.users.services.creation_service import (
    EtudiantCreationService,
    BibliothecaireCreationService,
)
from apps.users.repositories.profil_repositories import (
    EtudiantRepository,
    BibliothecaireRepository,
)
from apps.users.permissions import (
    IsAdministrateur,
    IsAdminOrBibliothecaire,
)


def _resp(result):
    return Response(
        {'success': result.success, 'message': result.message,
         'data': result.data or {}, 'errors': result.errors or {}},
        status=result.http_status
    )


# =============================================================================
# 🎓  CRÉATION ÉTUDIANT
# =============================================================================

class EtudiantCreateView(APIView):
    """
    POST /api/etudiants/
    Crée un nouveau compte étudiant.
    Accessible par Bibliothécaire (avec peut_gerer_utilisateurs) ou Admin.
    """
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]
    parser_classes     = [JSONParser, MultiPartParser]

    @extend_schema(
        tags=['Étudiants'],
        summary='Créer un compte étudiant',
        description="""
## Création d'un compte étudiant

**Qui peut créer ?**
- ✅ **Administrateur** — toujours autorisé
- ✅ **Bibliothécaire** avec `peut_gerer_utilisateurs = True`
- ❌ **Bibliothécaire** avec `peut_gerer_utilisateurs = False` → 403

---

## Règles métier

| Niveau | Spécialité requise ? |
|--------|----------------------|
| L1, L2, L3 | ❌ Non — tronc commun, laisser vide |
| M1, M2 | ✅ Oui — obligatoire |
| DOCTORAT | ✅ Oui — obligatoire |

---

## Ce qui est créé automatiquement

- **Matricule** : format `ETU + année + 5 chiffres` (ex: `ETU202512345`)
- **Secret TOTP** : pour Google Authenticator (retourné dans la réponse)
- **Compte** : inactif par défaut (`activer_immediatement: false`)

---

## Flux recommandé

```
1. POST /api/etudiants/               ← créer l'étudiant
2. Transmettre le QR code à l'étudiant
3. L'étudiant scanne et confirme : POST /api/auth/totp/confirm/
4. POST /api/etudiants/{id}/activer/  ← activer le compte
5. L'étudiant peut se connecter : POST /api/auth/etudiant/login/
```
        """,
        request=EtudiantCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Étudiant créé avec succès",
                response=inline_serializer('EtudiantCreateResponse', fields={
                    'success':   s.BooleanField(),
                    'message':   s.CharField(),
                    'data': inline_serializer('EtudiantCreateData', fields={
                        'etudiant_id':    s.UUIDField(help_text="UUID du profil étudiant"),
                        'user_id':        s.UUIDField(help_text="UUID du compte User"),
                        'matricule':      s.CharField(help_text="ETU202512345 (généré automatiquement)"),
                        'email':          s.EmailField(),
                        'nom_complet':    s.CharField(),
                        'statut_compte':  s.CharField(help_text="⚪ Jamais activé"),
                        'jours_restants': s.IntegerField(allow_null=True, help_text="null — pas encore activé"),
                        'compte_expire_le': s.DateTimeField(allow_null=True),
                        'totp_setup': inline_serializer('TOTPSetup', fields={
                            'totp_secret':  s.CharField(help_text="Secret base32 à scanner ou saisir manuellement"),
                            'qr_uri':       s.CharField(help_text="URI à encoder en QR code côté frontend"),
                            'instructions': s.CharField(),
                        })
                    })
                })
            ),
            400: OpenApiResponse(description="Email/téléphone déjà utilisé — niveau/spécialité incohérents"),
            403: OpenApiResponse(description="Permission insuffisante"),
        },
        examples=[
            # ── L1 tronc commun ───────────────────────────────────────────────
            OpenApiExample(
                'Créer un étudiant L1 (tronc commun)',
                description="Pas de spécialité pour le tronc commun L1/L2/L3.",
                request_only=True,
                value={
                    "first_name":           "Aminata",
                    "last_name":            "AMANI",
                    "email":                "etu.amani.l1@etud-ci.edu",
                    "phone":                "+2250702001001",
                    "date_of_birth":        "2004-06-15",
                    "password":             "Etudiant@2025!",
                    "confirm_password":     "Etudiant@2025!",
                    "niveau_id":            "uuid-du-niveau-L1",
                    "filiere_id":           "uuid-filiere-droit-general",
                    "specialite_id":        None,
                    "annee_inscription":    2025,
                    "activer_immediatement": False
                }
            ),
            # ── M2 spécialité ─────────────────────────────────────────────────
            OpenApiExample(
                'Créer un étudiant M2 (avec spécialité)',
                description="Spécialité obligatoire pour M1/M2/DOCTORAT.",
                request_only=True,
                value={
                    "first_name":           "Inès",
                    "last_name":            "IRIÉ",
                    "email":                "etu.irie.m2c@etud-ci.edu",
                    "phone":                "+2250702005001",
                    "date_of_birth":        "2000-03-20",
                    "password":             "Etudiant@2025!",
                    "confirm_password":     "Etudiant@2025!",
                    "niveau_id":            "uuid-du-niveau-M2",
                    "filiere_id":           "uuid-filiere-droit-des-contentieux",
                    "specialite_id":        "uuid-specialite-contentieux",
                    "annee_inscription":    2025,
                    "activer_immediatement": True
                }
            ),
            # ── Réponse succès ────────────────────────────────────────────────
            OpenApiExample(
                'Réponse — Création réussie',
                response_only=True, status_codes=['201'],
                value={
                    "success": True,
                    "message": "Compte étudiant créé avec succès. Matricule : ETU202512345. Compte inactif — activation manuelle requise.",
                    "data": {
                        "etudiant_id":    "550e8400-e29b-41d4-a716-446655440000",
                        "user_id":        "661e8400-e29b-41d4-a716-446655440111",
                        "matricule":      "ETU202512345",
                        "email":          "etu.amani.l1@etud-ci.edu",
                        "nom_complet":    "Aminata AMANI",
                        "statut_compte":  "⚪ Jamais activé",
                        "jours_restants": None,
                        "compte_expire_le": None,
                        "totp_setup": {
                            "totp_secret":  "JBSWY3DPEHPK3PXP",
                            "qr_uri":       "otpauth://totp/Biblioth%C3%A8que:etu.amani.l1%40etud-ci.edu?secret=JBSWY3DPEHPK3PXP&issuer=Biblioth%C3%A8que+Universitaire+CI",
                            "instructions": "Transmettez ces informations à l'étudiant pour qu'il configure Google Authenticator."
                        }
                    },
                    "errors": {}
                }
            ),
            # ── Erreur niveau/spécialité ──────────────────────────────────────
            OpenApiExample(
                'Erreur — Spécialité manquante pour M2',
                response_only=True, status_codes=['400'],
                value={
                    "success": False,
                    "message": "Une spécialité est obligatoire pour le niveau M2.",
                    "data":    {},
                    "errors":  {"specialite_id": ["Spécialité requise pour ce niveau."]}
                }
            ),
            OpenApiExample(
                'Erreur — Email déjà utilisé',
                response_only=True, status_codes=['400'],
                value={
                    "success": False,
                    "message": "Un compte avec cet email existe déjà.",
                    "data":    {},
                    "errors":  {"email": ["Email déjà utilisé par un autre compte."]}
                }
            ),
        ]
    )
    def post(self, request):
        # Vérifier permission spécifique bibliothécaire
        if (request.user.user_type == 'BIBLIOTHECAIRE'):
            try:
                bib = request.user.profil_bibliothecaire
                if not bib.peut_gerer_utilisateurs:
                    return Response({
                        'success': False,
                        'message': "Vous n'avez pas la permission de créer des utilisateurs. "
                                   "Contactez l'administrateur.",
                        'data': {}, 'errors': {}
                    }, status=403)
            except Exception:
                return Response({
                    'success': False, 'message': "Profil bibliothécaire introuvable.",
                    'data': {}, 'errors': {}
                }, status=403)

        serializer = EtudiantCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False, 'message': 'Données invalides.',
                'data': {}, 'errors': serializer.errors
            }, status=400)

        result = EtudiantCreationService.creer_etudiant(
            data          = serializer.validated_data,
            effectue_par  = request.user,
        )
        return _resp(result)


class EtudiantListView(APIView):
    """GET /api/etudiants/ — Liste des étudiants"""
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(
        tags=['Étudiants'],
        summary='Lister les étudiants',
        description="Retourne la liste paginée des étudiants avec filtres.",
        responses={200: OpenApiResponse(description="Liste des étudiants")},
    )
    def get(self, request):
        filters = {}
        if request.query_params.get('filiere'):
            filters['filiere__name__icontains'] = request.query_params['filiere']
        if request.query_params.get('niveau'):
            filters['niveau__name'] = request.query_params['niveau'].upper()
        if request.query_params.get('specialite'):
            filters['specialite__name__icontains'] = request.query_params['specialite']
        if request.query_params.get('expire') == 'true':
            from django.utils import timezone
            filters['compte_expire_le__lt'] = timezone.now()

        qs        = EtudiantRepository.get_all(filters)
        search    = request.query_params.get('search', '')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)  |
                Q(user__email__icontains=search)       |
                Q(matricule__icontains=search)
            )

        page      = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total     = qs.count()
        start     = (page - 1) * page_size

        serializer = EtudiantDetailSerializer(qs[start:start + page_size], many=True)
        return Response({
            'success': True, 'count': total, 'page': page,
            'pages': (total + page_size - 1) // page_size,
            'results': serializer.data
        })


class EtudiantDetailView(APIView):
    """GET/PATCH/DELETE /api/etudiants/<id>/"""
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]
    parser_classes     = [JSONParser]

    def _get_or_404(self, etudiant_id):
        etudiant = EtudiantRepository.get_by_id(etudiant_id)
        if not etudiant:
            return None, Response({
                'success': False, 'message': "Étudiant introuvable.",
                'data': {}, 'errors': {}
            }, status=404)
        return etudiant, None

    @extend_schema(tags=['Étudiants'], summary='Détail d\'un étudiant')
    def get(self, request, etudiant_id):
        etudiant, err = self._get_or_404(etudiant_id)
        if err: return err
        return Response({'success': True, 'data': EtudiantDetailSerializer(etudiant).data})

    @extend_schema(
        tags=['Étudiants'],
        summary='Modifier un étudiant (PATCH)',
        request=EtudiantUpdateSerializer,
        responses={200: OpenApiResponse(description="Profil mis à jour")},
        examples=[
            OpenApiExample('Changement de niveau',  request_only=True,
                value={'niveau_id': 'uuid-niveau-M1', 'specialite_id': 'uuid-specialite-contentieux'}),
        ]
    )
    def patch(self, request, etudiant_id):
        etudiant, err = self._get_or_404(etudiant_id)
        if err: return err

        serializer = EtudiantUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        data = serializer.validated_data
        user_fields    = {}
        profil_fields  = {}

        for f in ('first_name', 'last_name', 'phone', 'date_of_birth'):
            if f in data:
                user_fields[f] = data[f]

        from apps.users.repositories.user_repository import UserRepository
        if user_fields:
            UserRepository.update(etudiant.user, **user_fields)

        for fk, model_field in [('filiere_id', 'filiere'), ('niveau_id', 'niveau'), ('specialite_id', 'specialite')]:
            if fk in data:
                profil_fields[model_field + '_id'] = data[fk]
        if profil_fields:
            EtudiantRepository.update(etudiant, **profil_fields)

        from logs.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=etudiant.user,
                            details={'champs': list(data.keys())})

        return Response({'success': True, 'message': 'Profil étudiant mis à jour.',
                         'data': EtudiantDetailSerializer(etudiant).data})

    @extend_schema(tags=['Étudiants'], summary='Supprimer un étudiant (soft delete)')
    def delete(self, request, etudiant_id):
        etudiant, err = self._get_or_404(etudiant_id)
        if err: return err
        if request.user.user_type != 'ADMINISTRATEUR':
            return Response({'success': False, 'message': "Seul l'administrateur peut supprimer un compte.",
                             'data': {}, 'errors': {}}, status=403)

        from logs.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=etudiant.user)
        EtudiantRepository.soft_delete(etudiant)
        return Response({'success': True, 'message': "Compte étudiant supprimé.", 'data': {}, 'errors': {}}, status=204)


class EtudiantActiverView(APIView):
    """
    POST /api/etudiants/<id>/activer/
    Active ou réactive le compte d'un étudiant.
    """
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(
        tags=['Étudiants'],
        summary='Activer / Réactiver un compte étudiant',
        description="""
## Activation / Réactivation

| Action | Quand l'utiliser | Effet |
|--------|-----------------|-------|
| `activer` | Premier démarrage du compte | Démarre le cycle de 30 jours |
| `reactiver` | Compte expiré | Repart pour 30 jours depuis aujourd'hui |

> **Note :** `activer` échoue si le compte a déjà été activé une fois.
> Dans ce cas, utilisez `reactiver`.
        """,
        request=EtudiantActiverSerializer,
        responses={
            200: OpenApiResponse(
                description="Compte activé / réactivé",
                response=inline_serializer('ActivationResponse', fields={
                    'data': inline_serializer('ActivationData', fields={
                        'matricule':        s.CharField(),
                        'statut_compte':    s.CharField(help_text="✅ Actif (30 jours restants)"),
                        'jours_restants':   s.IntegerField(),
                        'compte_active_le': s.DateTimeField(),
                        'compte_expire_le': s.DateTimeField(),
                        'nb_reactivations': s.IntegerField(),
                    })
                })
            ),
            400: OpenApiResponse(description="Compte déjà activé (utiliser 'reactiver')"),
            404: OpenApiResponse(description="Étudiant introuvable"),
        },
        examples=[
            OpenApiExample('Première activation', request_only=True,
                value={'action': 'activer'}),
            OpenApiExample('Réactivation', request_only=True,
                value={'action': 'reactiver'}),
            OpenApiExample('Réponse succès', response_only=True, status_codes=['200'],
                value={
                    'success': True,
                    'message': 'Compte de Inès IRIÉ activé. Expire le 26/04/2025.',
                    'data': {
                        'matricule':        'ETU202512345',
                        'statut_compte':    '✅ Actif (30 jours restants)',
                        'jours_restants':   30,
                        'compte_active_le': '2025-03-27T10:00:00Z',
                        'compte_expire_le': '2025-04-26T10:00:00Z',
                        'nb_reactivations': 0,
                    },
                    'errors': {}
                }),
        ]
    )
    def post(self, request, etudiant_id):
        # Vérifier permission biblio
        if request.user.user_type == 'BIBLIOTHECAIRE':
            try:
                if not request.user.profil_bibliothecaire.peut_gerer_utilisateurs:
                    return Response({
                        'success': False,
                        'message': "Vous n'avez pas la permission de gérer les utilisateurs.",
                        'data': {}, 'errors': {}
                    }, status=403)
            except Exception:
                return Response({'success': False, 'message': "Profil bibliothécaire introuvable.",
                                 'data': {}, 'errors': {}}, status=403)

        serializer = EtudiantActiverSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        result = EtudiantCreationService.activer_compte(
            etudiant_id  = str(etudiant_id),
            effectue_par = request.user,
            action       = serializer.validated_data['action'],
        )
        return _resp(result)


# =============================================================================
# 📖  CRÉATION BIBLIOTHÉCAIRE
# =============================================================================

class BibliothecaireCreateView(APIView):
    """
    POST /api/bibliothecaires/
    Crée un nouveau compte bibliothécaire.
    Réservé à l'administrateur uniquement.
    """
    permission_classes = [IsAuthenticated, IsAdministrateur]
    parser_classes     = [JSONParser]

    @extend_schema(
        tags=['Bibliothécaires'],
        summary='Créer un compte bibliothécaire',
        description="""
## Création d'un compte bibliothécaire

**Réservé à l'administrateur uniquement.**

---

## Ce qui est créé automatiquement

- Compte User avec `user_type = BIBLIOTHECAIRE`, `is_staff = True`
- Profil Bibliothecaire avec les permissions définies
- **Secret TOTP** pré-généré (Google Authenticator)

## Flux recommandé

```
1. POST /api/bibliothecaires/         ← admin crée le compte
2. Transmettre QR code au bibliothécaire
3. Biblio scanne : POST /api/auth/totp/confirm/   ← active le 2FA
4. Biblio se connecte : POST /api/auth/bibliothecaire/login/
```

## Permissions disponibles

| Permission | Défaut | Description |
|------------|--------|-------------|
| `peut_gerer_documents` | ✅ True | Ajouter/modifier/supprimer des documents |
| `peut_gerer_utilisateurs` | ❌ False | Créer et activer des comptes étudiants |
        """,
        request=BibliothecaireCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Bibliothécaire créé avec succès",
                response=inline_serializer('BibliothecaireCreateResponse', fields={
                    'success':   s.BooleanField(),
                    'message':   s.CharField(),
                    'data': inline_serializer('BibliothecaireCreateData', fields={
                        'bibliothecaire_id': s.UUIDField(),
                        'user_id':           s.UUIDField(),
                        'email':             s.EmailField(),
                        'nom_complet':       s.CharField(),
                        'badge_number':      s.CharField(allow_null=True),
                        'permissions': inline_serializer('BiblioPerms', fields={
                            'peut_gerer_documents':    s.BooleanField(),
                            'peut_gerer_utilisateurs': s.BooleanField(),
                        }),
                        'totp_setup': inline_serializer('TOTPSetup2', fields={
                            'totp_secret':  s.CharField(),
                            'qr_uri':       s.CharField(),
                            'instructions': s.CharField(),
                        })
                    })
                })
            ),
            400: OpenApiResponse(description="Email/téléphone/badge déjà utilisé"),
            403: OpenApiResponse(description="Réservé à l'administrateur"),
        },
        examples=[
            OpenApiExample(
                'Créer un bibliothécaire avec toutes les permissions',
                request_only=True,
                value={
                    "first_name":               "Mariam",
                    "last_name":                "KONÉ",
                    "email":                    "biblio.kone@universite-ci.edu",
                    "phone":                    "+2250701000002",
                    "date_of_birth":            "1990-05-20",
                    "password":                 "Biblio@2025!",
                    "confirm_password":         "Biblio@2025!",
                    "badge_number":             "BIB-2025-003",
                    "date_prise_poste":         "2025-01-06",
                    "peut_gerer_documents":     True,
                    "peut_gerer_utilisateurs":  True
                }
            ),
            OpenApiExample(
                'Créer un bibliothécaire (documents seulement)',
                request_only=True,
                value={
                    "first_name":               "Seydou",
                    "last_name":                "DIALLO",
                    "email":                    "biblio.diallo@universite-ci.edu",
                    "phone":                    "+2250701000003",
                    "password":                 "Biblio@2025!",
                    "confirm_password":         "Biblio@2025!",
                    "badge_number":             "BIB-2025-004",
                    "peut_gerer_documents":     True,
                    "peut_gerer_utilisateurs":  False
                }
            ),
            OpenApiExample(
                'Réponse — Création réussie',
                response_only=True, status_codes=['201'],
                value={
                    "success": True,
                    "message": "Compte bibliothécaire créé avec succès pour Mariam KONÉ. Le bibliothécaire doit configurer Google Authenticator à sa première connexion.",
                    "data": {
                        "bibliothecaire_id": "771e8400-e29b-41d4-a716-446655440333",
                        "user_id":           "882e8400-e29b-41d4-a716-446655440444",
                        "email":             "biblio.kone@universite-ci.edu",
                        "nom_complet":       "Mariam KONÉ",
                        "badge_number":      "BIB-2025-003",
                        "permissions": {
                            "peut_gerer_documents":    True,
                            "peut_gerer_utilisateurs": True
                        },
                        "totp_setup": {
                            "totp_secret": "JBSWY3DPEHPK3PXP",
                            "qr_uri":      "otpauth://totp/Biblioth%C3%A8que:biblio.kone%40universite-ci.edu?secret=JBSWY3DPEHPK3PXP&issuer=Biblioth%C3%A8que+Universitaire+CI",
                            "instructions": "Transmettez ces informations au bibliothécaire. Il devra scanner ce QR code avec Google Authenticator et confirmer via POST /api/auth/totp/confirm/."
                        }
                    },
                    "errors": {}
                }
            ),
            OpenApiExample(
                'Erreur — Badge déjà utilisé',
                response_only=True, status_codes=['400'],
                value={
                    "success": False,
                    "message": "Le badge 'BIB-2025-003' est déjà assigné à un autre bibliothécaire.",
                    "data":    {},
                    "errors":  {"badge_number": ["Numéro de badge déjà utilisé."]}
                }
            ),
        ]
    )
    def post(self, request):
        serializer = BibliothecaireCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        result = BibliothecaireCreationService.creer_bibliothecaire(
            data         = serializer.validated_data,
            effectue_par = request.user,
        )
        return _resp(result)


class BibliothecaireListView(APIView):
    """GET /api/bibliothecaires/ — Liste des bibliothécaires [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(tags=['Bibliothécaires'], summary='Lister les bibliothécaires')
    def get(self, request):
        qs         = BibliothecaireRepository.get_all()
        serializer = BibliothecaireDetailSerializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'results': serializer.data})


class BibliothecaireDetailView(APIView):
    """GET/PATCH/DELETE /api/bibliothecaires/<id>/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    def _get_or_404(self, biblio_id):
        b = BibliothecaireRepository.get_by_id(biblio_id)
        if not b:
            return None, Response({'success': False, 'message': "Bibliothécaire introuvable.",
                                   'data': {}, 'errors': {}}, status=404)
        return b, None

    @extend_schema(tags=['Bibliothécaires'], summary='Détail d\'un bibliothécaire')
    def get(self, request, biblio_id):
        b, err = self._get_or_404(biblio_id)
        if err: return err
        return Response({'success': True, 'data': BibliothecaireDetailSerializer(b).data})

    @extend_schema(
        tags=['Bibliothécaires'],
        summary='Modifier un bibliothécaire (PATCH)',
        request=BibliothecaireUpdateSerializer,
        examples=[
            OpenApiExample('Modifier les permissions', request_only=True,
                value={'peut_gerer_utilisateurs': True, 'badge_number': 'BIB-2025-005'}),
        ]
    )
    def patch(self, request, biblio_id):
        b, err = self._get_or_404(biblio_id)
        if err: return err

        serializer = BibliothecaireUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        data = serializer.validated_data
        user_fields   = {f: data[f] for f in ('first_name', 'last_name', 'phone', 'date_of_birth') if f in data}
        profil_fields = {f: data[f] for f in ('badge_number', 'date_prise_poste', 'peut_gerer_documents', 'peut_gerer_utilisateurs') if f in data}

        from apps.users.repositories.user_repository import UserRepository
        if user_fields:
            UserRepository.update(b.user, **user_fields)
        if profil_fields:
            BibliothecaireRepository.update(b, **profil_fields)

        from logs.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=b.user,
                            details={'champs': list(data.keys())})
        return Response({'success': True, 'message': 'Profil bibliothécaire mis à jour.',
                         'data': BibliothecaireDetailSerializer(b).data})

    @extend_schema(tags=['Bibliothécaires'], summary='Supprimer un bibliothécaire (soft delete)')
    def delete(self, request, biblio_id):
        b, err = self._get_or_404(biblio_id)
        if err: return err
        from logs.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=b.user)
        BibliothecaireRepository.soft_delete(b)
        return Response({'success': True, 'message': "Compte bibliothécaire supprimé.",
                         'data': {}, 'errors': {}}, status=204)²