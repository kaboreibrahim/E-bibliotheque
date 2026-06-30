
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
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone

from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse,
    OpenApiTypes, inline_serializer
)
from rest_framework import serializers as s

from apps.users.serializers.creation_serializers import (
    EtudiantCreateSerializer,
    EtudiantUpdateSerializer,
    EtudiantActiverSerializer,
    EtudiantDetailSerializer,
    PersonneExterneCreateSerializer,
    PersonneExterneUpdateSerializer,
    PersonneExterneDetailSerializer,
    BibliothecaireCreateSerializer,
    BibliothecaireUpdateSerializer,
    BibliothecaireDetailSerializer,
    EnseignantChercheurCreateSerializer,
    EnseignantChercheurUpdateSerializer,
    EnseignantChercheurDetailSerializer,
    ChercheurCreateSerializer,
    ChercheurUpdateSerializer,
    ChercheurDetailSerializer,
)
from apps.users.services.creation_service import (
    EtudiantCreationService,
    PersonneExterneCreationService,
    BibliothecaireCreationService,
    EnseignantChercheurCreationService,
    ChercheurCreationService,
)
from apps.users.services.etudiant_export_service import EtudiantExcelExportService
from apps.users.repositories.etudiant_repository import (
    EtudiantRepository,
    BibliothecaireRepository,
)
from apps.users.repositories.personne_repository import (
    PersonneExterneRepository,
    EnseignantChercheurRepository,
    ChercheurRepository,
)
from apps.users.permissions import (
    IsAdministrateur,
    IsAdminOrBibliothecaire,
)
from apps.history.models import HistoriqueActionService as HAS
from django.db.models import Q


ETUDIANT_ID_PARAMETER = OpenApiParameter(
    name='etudiant_id',
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID du profil etudiant, pas le user_id.",
    examples=[
        OpenApiExample(
            'UUID du profil etudiant',
            value='550e8400-e29b-41d4-a716-446655440000',
            parameter_only=('etudiant_id', 'path'),
        )
    ],
)

BIBLIO_ID_PARAMETER = OpenApiParameter(
    name='biblio_id',
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="UUID du profil bibliothecaire, pas le user_id.",
    examples=[
        OpenApiExample(
            'UUID du profil bibliothecaire',
            value='771e8400-e29b-41d4-a716-446655440333',
            parameter_only=('biblio_id', 'path'),
        )
    ],
)

ETUDIANT_DETAIL_RESPONSE = inline_serializer(
    'EtudiantDetailEnvelope',
    fields={
        'success': s.BooleanField(),
        'data': EtudiantDetailSerializer(),
    },
)

BIBLIOTHECAIRE_DETAIL_RESPONSE = inline_serializer(
    'BibliothecaireDetailEnvelope',
    fields={
        'success': s.BooleanField(),
        'data': BibliothecaireDetailSerializer(),
    },
)

PERSONNE_EXTERNE_DETAIL_RESPONSE = inline_serializer(
    'PersonneExterneDetailEnvelope',
    fields={
        'success': s.BooleanField(),
        'data': PersonneExterneDetailSerializer(),
    },
)

ETUDIANT_LIST_PARAMETERS = [
    OpenApiParameter(
        name='filiere',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Filtrer par nom de filiere.",
    ),
    OpenApiParameter(
        name='niveau',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Filtrer par code niveau. Ex: L1, L2, M1, M2.",
    ),
    OpenApiParameter(
        name='specialite',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Filtrer par nom de specialite.",
    ),
    OpenApiParameter(
        name='expire',
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        required=False,
        description="`true` pour exporter uniquement les comptes expires.",
    ),
    OpenApiParameter(
        name='search',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Recherche sur prenom, nom, email ou matricule.",
    ),
]


def _resp(result):
    return Response(
        {'success': result.success, 'message': result.message,
         'data': result.data or {}, 'errors': result.errors or {}},
        status=result.http_status
    )


def _build_etudiant_queryset(request):
    filters = {}
    if request.query_params.get('filiere'):
        filters['filiere__name__icontains'] = request.query_params['filiere']
    if request.query_params.get('niveau'):
        filters['niveau__name'] = request.query_params['niveau'].upper()
    if request.query_params.get('specialite'):
        filters['specialite__name__icontains'] = request.query_params['specialite']
    if request.query_params.get('expire') == 'true':
        filters['compte_expire_le__lt'] = timezone.now()

    queryset = EtudiantRepository.get_all(filters)
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(matricule__icontains=search)
        )
    return queryset


def _build_personne_externe_queryset(request):
    queryset = PersonneExterneRepository.get_all()
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(numero_piece__icontains=search)
            | Q(profession__icontains=search)
            | Q(lieu_habitation__icontains=search)
        )
    return queryset


def _build_enseignant_chercheur_queryset(request):
    queryset = EnseignantChercheurRepository.get_all()
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(specialite_enseignee__icontains=search)
            | Q(lieu_habitation__icontains=search)
        )
    if request.query_params.get('suspendu') == 'true':
        queryset = queryset.filter(activation_suspendue=True)
    return queryset


def _build_chercheur_queryset(request):
    queryset = ChercheurRepository.get_all()
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(specialite_enseignee__icontains=search)
            | Q(lieu_habitation__icontains=search)
        )
    if request.query_params.get('suspendu') == 'true':
        queryset = queryset.filter(activation_suspendue=True)
    return queryset


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
| L1, L2, L3, M1, M2, DOCTORAT | ✅ Oui — obligatoire |

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
            # ── L3 spécialité ─────────────────────────────────────────────────
            OpenApiExample(
                'Créer un étudiant L3 (avec spécialité)',
                description="Spécialité obligatoire pour L3 aussi.",
                request_only=True,
                value={
                    "first_name":           "Aminata",
                    "last_name":            "AMANI",
                    "email":                "etu.amani.l3@etud-ci.edu",
                    "phone":                "+2250702001001",
                    "date_of_birth":        "2004-06-15",
                    "password":             "Etudiant@2025!",
                    "confirm_password":     "Etudiant@2025!",
                    "niveau_id":            "uuid-du-niveau-L3",
                    "filiere_id":           "uuid-filiere-droit-des-affaires",
                    "specialite_id":        "uuid-specialite-droit-des-affaires-l3",
                    "annee_inscription":    2025,
                    "activer_immediatement": False
                }
            ),
            OpenApiExample(
                'Créer un étudiant L1 (avec spécialité)',
                description="Spécialité obligatoire pour L1, L2, L3, M1, M2 et DOCTORAT.",
                request_only=True,
                value={
                    "first_name":           "Aminata",
                    "last_name":            "AMANI",
                    "email":                "etu.amani.l1@etud-ci.edu",
                    "phone":                "+2250702001002",
                    "date_of_birth":        "2004-06-15",
                    "password":             "Etudiant@2025!",
                    "confirm_password":     "Etudiant@2025!",
                    "niveau_id":            "uuid-du-niveau-L1",
                    "filiere_id":           "uuid-filiere-droit-des-affaires",
                    "specialite_id":        "uuid-specialite-droit-des-affaires-l1",
                    "annee_inscription":    2025,
                    "activer_immediatement": False
                }
            ),
            # ── M2 spécialité ─────────────────────────────────────────────────
            OpenApiExample(
                'Créer un étudiant M2 (avec spécialité)',
                description="Spécialité obligatoire pour L1/L2/L3/M1/M2/DOCTORAT.",
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
        parameters=ETUDIANT_LIST_PARAMETERS,
        responses={200: OpenApiResponse(description="Liste des étudiants")},
    )
    def get(self, request):
        qs = _build_etudiant_queryset(request)

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


class EtudiantExportExcelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(
        tags=['Étudiants'],
        summary='Exporter les étudiants en Excel',
        description=(
            "Télécharge un fichier `.xlsx` contenant la liste des étudiants et des "
            "personnes externes avec leurs informations personnelles, académiques "
            "quand elles existent, et le type de profil."
        ),
        parameters=ETUDIANT_LIST_PARAMETERS,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Fichier Excel des étudiants.",
            ),
            403: OpenApiResponse(description="Accès réservé aux administrateurs et bibliothécaires."),
        },
    )
    def get(self, request):
        etudiants = _build_etudiant_queryset(request)
        academic_filters = any(
            request.query_params.get(param)
            for param in ('filiere', 'niveau', 'specialite', 'expire')
        )
        personnes_externes = (
            PersonneExterneRepository.get_all().none()
            if academic_filters
            else _build_personne_externe_queryset(request)
        )
        workbook = EtudiantExcelExportService.export(etudiants, personnes_externes)
        filename = f'profils_{timezone.localdate().isoformat()}.xlsx'

        response = HttpResponse(
            workbook,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PersonneExterneCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]
    parser_classes = [JSONParser, MultiPartParser]

    @extend_schema(
        tags=['Personnes externes'],
        summary='Créer une personne externe',
        description=(
            "Crée un compte de personne externe. Aucun niveau ni aucune spécialité "
            "ne sont requis et le compte peut consulter tous les documents."
        ),
        request=PersonneExterneCreateSerializer,
        responses={
            201: OpenApiResponse(description="Personne externe créée avec succès."),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Permission insuffisante."),
        },
    )
    def post(self, request):
        if request.user.user_type == 'BIBLIOTHECAIRE':
            try:
                bib = request.user.profil_bibliothecaire
                if not bib.peut_gerer_utilisateurs:
                    return Response({
                        'success': False,
                        'message': "Vous n'avez pas la permission de créer des utilisateurs.",
                        'data': {},
                        'errors': {},
                    }, status=403)
            except Exception:
                return Response({
                    'success': False,
                    'message': "Profil bibliothécaire introuvable.",
                    'data': {},
                    'errors': {},
                }, status=403)

        serializer = PersonneExterneCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Données invalides.',
                'data': {},
                'errors': serializer.errors,
            }, status=400)

        result = PersonneExterneCreationService.creer_personne_externe(
            data=serializer.validated_data,
            effectue_par=request.user,
        )
        return _resp(result)


class PersonneExterneListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(
        tags=['Personnes externes'],
        summary='Lister les personnes externes',
        description="Retourne la liste paginée des personnes externes.",
        responses={200: OpenApiResponse(description="Liste des personnes externes.")},
    )
    def get(self, request):
        queryset = _build_personne_externe_queryset(request)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        start = (page - 1) * page_size

        serializer = PersonneExterneDetailSerializer(
            queryset[start:start + page_size],
            many=True,
        )
        return Response({
            'success': True,
            'count': total,
            'page': page,
            'pages': (total + page_size - 1) // page_size,
            'results': serializer.data,
        })


class PersonneExterneDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]
    parser_classes = [JSONParser]

    def _get_or_404(self, personne_id):
        personne = PersonneExterneRepository.get_by_id(personne_id)
        if not personne:
            return None, Response({
                'success': False,
                'message': "Personne externe introuvable.",
                'data': {},
                'errors': {},
            }, status=404)
        return personne, None

    @extend_schema(
        tags=['Personnes externes'],
        summary="Détail d'une personne externe",
        responses={
            200: OpenApiResponse(
                description="Détail de la personne externe.",
                response=PERSONNE_EXTERNE_DETAIL_RESPONSE,
            ),
            404: OpenApiResponse(description="Personne externe introuvable."),
        },
    )
    def get(self, request, personne_id):
        personne, err = self._get_or_404(personne_id)
        if err:
            return err
        return Response({
            'success': True,
            'data': PersonneExterneDetailSerializer(personne).data,
        })

    @extend_schema(
        tags=['Personnes externes'],
        summary="Modifier une personne externe",
        request=PersonneExterneUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="Profil mis à jour.",
                response=PERSONNE_EXTERNE_DETAIL_RESPONSE,
            ),
            400: OpenApiResponse(description="Données invalides."),
            404: OpenApiResponse(description="Personne externe introuvable."),
        },
    )
    def patch(self, request, personne_id):
        personne, err = self._get_or_404(personne_id)
        if err:
            return err

        serializer = PersonneExterneUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Données invalides.',
                'data': {},
                'errors': serializer.errors,
            }, status=400)

        data = serializer.validated_data
        user_fields = {
            field: data[field]
            for field in ('first_name', 'last_name', 'phone', 'date_of_birth')
            if field in data
        }
        profil_fields = {
            field: data[field]
            for field in (
                'numero_piece',
                'profession',
                'lieu_habitation',
                'date_debut_validite',
                'date_fin_validite',
            )
            if field in data
        }

        if (
            ('date_debut_validite' in data or 'date_fin_validite' in data)
            and personne.compte_active_le is None
            and (
                data.get('date_debut_validite', personne.date_debut_validite)
                and data.get('date_fin_validite', personne.date_fin_validite)
            )
        ):
            profil_fields['compte_active_le'] = timezone.now()
            profil_fields['activation_suspendue'] = False

        from apps.users.repositories.user_repository import UserRepository
        if user_fields:
            UserRepository.update(personne.user, **user_fields)
        if profil_fields:
            try:
                PersonneExterneRepository.update(personne, **profil_fields)
            except ValidationError as exc:
                return Response({
                    'success': False,
                    'message': 'Données invalides.',
                    'data': {},
                    'errors': exc.message_dict,
                }, status=400)

        HAS.log_utilisateur(
            'MODIF',
            auteur=request.user,
            cible_user=personne.user,
            details={'champs': list(data.keys())},
        )

        return Response({
            'success': True,
            'message': 'Profil personne externe mis à jour.',
            'data': PersonneExterneDetailSerializer(personne).data,
        })

    @extend_schema(
        tags=['Personnes externes'],
        summary='Supprimer une personne externe (soft delete)',
        responses={
            204: OpenApiResponse(description="Compte supprimé."),
            403: OpenApiResponse(description="Réservé à l'administrateur."),
            404: OpenApiResponse(description="Personne externe introuvable."),
        },
    )
    def delete(self, request, personne_id):
        personne, err = self._get_or_404(personne_id)
        if err:
            return err
        if request.user.user_type != 'ADMINISTRATEUR':
            return Response({
                'success': False,
                'message': "Seul l'administrateur peut supprimer un compte.",
                'data': {},
                'errors': {},
            }, status=403)

        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=personne.user)
        PersonneExterneRepository.soft_delete(personne)
        return Response({
            'success': True,
            'message': "Compte personne externe supprimé.",
            'data': {},
            'errors': {},
        }, status=204)


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

    @extend_schema(
        tags=['Étudiants'],
        summary='Détail d\'un étudiant',
        parameters=[ETUDIANT_ID_PARAMETER],
        responses={
            200: OpenApiResponse(
                description="Detail de l'etudiant",
                response=ETUDIANT_DETAIL_RESPONSE,
            ),
            404: OpenApiResponse(description="Etudiant introuvable"),
        },
    )
    def get(self, request, etudiant_id):
        etudiant, err = self._get_or_404(etudiant_id)
        if err: return err
        return Response({'success': True, 'data': EtudiantDetailSerializer(etudiant).data})

    @extend_schema(
        tags=['Étudiants'],
        summary='Modifier un étudiant (PATCH)',
        parameters=[ETUDIANT_ID_PARAMETER],
        request=EtudiantUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="Profil mis a jour",
                response=ETUDIANT_DETAIL_RESPONSE,
            ),
            400: OpenApiResponse(description="Donnees invalides"),
            404: OpenApiResponse(description="Etudiant introuvable"),
        },
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
        for field in ('date_debut_validite', 'date_fin_validite'):
            if field in data:
                profil_fields[field] = data[field]
        if profil_fields:
            try:
                EtudiantRepository.update(etudiant, **profil_fields)
            except ValidationError as exc:
                return Response({
                    'success': False,
                    'message': 'Données invalides.',
                    'data': {},
                    'errors': exc.message_dict,
                }, status=400)

        from apps.history.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=etudiant.user,
                            details={'champs': list(data.keys())})

        return Response({'success': True, 'message': 'Profil étudiant mis à jour.',
                         'data': EtudiantDetailSerializer(etudiant).data})

    @extend_schema(
        tags=['Étudiants'],
        summary='Supprimer un étudiant (soft delete)',
        parameters=[ETUDIANT_ID_PARAMETER],
        responses={
            204: OpenApiResponse(description="Compte etudiant supprime"),
            403: OpenApiResponse(description="Reserve a l'administrateur"),
            404: OpenApiResponse(description="Etudiant introuvable"),
        },
    )
    def delete(self, request, etudiant_id):
        etudiant, err = self._get_or_404(etudiant_id)
        if err: return err
        if request.user.user_type != 'ADMINISTRATEUR':
            return Response({'success': False, 'message': "Seul l'administrateur peut supprimer un compte.",
                             'data': {}, 'errors': {}}, status=403)

        from apps.history.models import HistoriqueActionService as HAS
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
        parameters=[ETUDIANT_ID_PARAMETER],
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
2. Option A : transmettre tout de suite le QR code retourne dans cette reponse
3. Option B : laisser le bibliothecaire se connecter une premiere fois ;
   `/api/auth/bibliothecaire/login/` retournera alors `requires_totp_setup`
   avec `setup_token` + `totp_setup`
4. POST /api/auth/totp/confirm/       ← active le 2FA
5. POST /api/auth/bibliothecaire/login/ puis /totp/verify/ pour les connexions suivantes
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

    @extend_schema(
        tags=['Bibliothécaires'],
        summary='Détail d\'un bibliothécaire',
        parameters=[BIBLIO_ID_PARAMETER],
        responses={
            200: OpenApiResponse(
                description="Detail du bibliothecaire",
                response=BIBLIOTHECAIRE_DETAIL_RESPONSE,
            ),
            404: OpenApiResponse(description="Bibliothecaire introuvable"),
        },
    )
    def get(self, request, biblio_id):
        b, err = self._get_or_404(biblio_id)
        if err: return err
        return Response({'success': True, 'data': BibliothecaireDetailSerializer(b).data})

    @extend_schema(
        tags=['Bibliothécaires'],
        summary='Modifier un bibliothécaire (PATCH)',
        parameters=[BIBLIO_ID_PARAMETER],
        request=BibliothecaireUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="Profil mis a jour",
                response=BIBLIOTHECAIRE_DETAIL_RESPONSE,
            ),
            400: OpenApiResponse(description="Donnees invalides"),
            404: OpenApiResponse(description="Bibliothecaire introuvable"),
        },
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

        from apps.history.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=b.user,
                            details={'champs': list(data.keys())})
        return Response({'success': True, 'message': 'Profil bibliothécaire mis à jour.',
                         'data': BibliothecaireDetailSerializer(b).data})

    @extend_schema(
        tags=['Bibliothécaires'],
        summary='Supprimer un bibliothécaire (soft delete)',
        parameters=[BIBLIO_ID_PARAMETER],
        responses={
            204: OpenApiResponse(description="Compte bibliothecaire supprime"),
            404: OpenApiResponse(description="Bibliothecaire introuvable"),
        },
    )
    def delete(self, request, biblio_id):
        b, err = self._get_or_404(biblio_id)
        if err: return err
        from apps.history.models import HistoriqueActionService as HAS
        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=b.user)
        BibliothecaireRepository.soft_delete(b)
        return Response({'success': True, 'message': "Compte bibliothécaire supprimé.",
                         'data': {}, 'errors': {}}, status=204)


# =============================================================================
# 👨‍🏫  ENSEIGNANT-CHERCHEUR VIEWS (Admin uniquement)
# =============================================================================

class EnseignantChercheurCreateView(APIView):
    """POST /api/enseignants-chercheurs/ — Créer un enseignant-chercheur [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]
    parser_classes = [JSONParser]

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary='Créer un compte enseignant-chercheur',
        description="""
## Création d'un compte enseignant-chercheur

**Réservé à l'administrateur uniquement.**

Le compte est créé actif immédiatement. Un secret TOTP (Google Authenticator) est généré
et retourné dans la réponse — transmettez-le à l'enseignant-chercheur pour qu'il configure
son application avant sa première connexion.

## Flux recommandé

```
1. POST /api/enseignants-chercheurs/               ← admin crée le compte
2. Transmettre le QR code / secret TOTP à l'intéressé
3. POST /api/auth/totp/confirm/                    ← active le 2FA
4. POST /api/auth/enseignant-chercheur/login/      ← connexion email + password
5. POST /api/auth/enseignant-chercheur/totp/verify/ ← vérification TOTP
```
        """,
        request=EnseignantChercheurCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Enseignant-chercheur créé avec succès.",
                response=inline_serializer('EnseignantChercheurCreateResponse', fields={
                    'success': s.BooleanField(),
                    'message': s.CharField(),
                    'data': inline_serializer('EnseignantChercheurCreateData', fields={
                        'enseignant_chercheur_id': s.UUIDField(),
                        'user_id': s.UUIDField(),
                        'email': s.EmailField(),
                        'nom_complet': s.CharField(),
                        'user_type': s.CharField(),
                        'statut_compte': s.CharField(),
                        'annee_service': s.IntegerField(allow_null=True),
                        'specialite_enseignee': s.CharField(),
                        'totp_setup': inline_serializer('TOTPSetupEC', fields={
                            'totp_secret': s.CharField(),
                            'qr_uri': s.CharField(),
                            'instructions': s.CharField(),
                        }),
                    }),
                }),
            ),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Réservé à l'administrateur."),
        },
        examples=[
            OpenApiExample(
                'Créer un enseignant-chercheur',
                request_only=True,
                value={
                    "first_name": "Ibrahim",
                    "last_name": "KABORÉ",
                    "email": "i.kabore@universite.bf",
                    "phone": "+22670100001",
                    "date_of_birth": "1980-05-15",
                    "password": "Enseignant@2025!",
                    "confirm_password": "Enseignant@2025!",
                    "numero_piece": "CNIB12345678",
                    "lieu_habitation": "Ouagadougou",
                    "annee_service": 2015,
                    "specialite_enseignee": "Informatique Théorique",
                },
            ),
        ],
    )
    def post(self, request):
        serializer = EnseignantChercheurCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)
        result = EnseignantChercheurCreationService.creer(
            data=serializer.validated_data, effectue_par=request.user
        )
        return _resp(result)


EC_LIST_PARAMETERS = [
    OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                     required=False, description="Recherche sur prénom, nom, email ou spécialité."),
    OpenApiParameter(name='suspendu', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY,
                     required=False, description="`true` pour filtrer les comptes suspendus."),
    OpenApiParameter(name='page', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='page_size', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
]


class EnseignantChercheurListView(APIView):
    """GET /api/enseignants-chercheurs/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary='Lister les enseignants-chercheurs',
        parameters=EC_LIST_PARAMETERS,
        responses={200: OpenApiResponse(description="Liste des enseignants-chercheurs.")},
    )
    def get(self, request):
        qs = _build_enseignant_chercheur_queryset(request)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = qs.count()
        start = (page - 1) * page_size
        serializer = EnseignantChercheurDetailSerializer(qs[start:start + page_size], many=True)
        return Response({
            'success': True, 'count': total, 'page': page,
            'pages': (total + page_size - 1) // page_size,
            'results': serializer.data,
        })


class EnseignantChercheurDetailView(APIView):
    """GET/PATCH/DELETE /api/enseignants-chercheurs/<id>/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]
    parser_classes = [JSONParser]

    def _get_or_404(self, pk):
        obj = EnseignantChercheurRepository.get_by_id(pk)
        if not obj:
            return None, Response({'success': False, 'message': "Enseignant-chercheur introuvable.",
                                   'data': {}, 'errors': {}}, status=404)
        return obj, None

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary="Détail d'un enseignant-chercheur",
        responses={200: OpenApiResponse(description="Détail.", response=EnseignantChercheurDetailSerializer)},
    )
    def get(self, request, enseignant_id):
        obj, err = self._get_or_404(enseignant_id)
        if err: return err
        return Response({'success': True, 'data': EnseignantChercheurDetailSerializer(obj).data})

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary='Modifier un enseignant-chercheur (PATCH)',
        request=EnseignantChercheurUpdateSerializer,
        responses={200: OpenApiResponse(description="Profil mis à jour.")},
    )
    def patch(self, request, enseignant_id):
        obj, err = self._get_or_404(enseignant_id)
        if err: return err

        serializer = EnseignantChercheurUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        data = serializer.validated_data
        user_fields = {f: data[f] for f in ('first_name', 'last_name', 'phone', 'date_of_birth') if f in data}
        profil_fields = {f: data[f] for f in ('numero_piece', 'lieu_habitation', 'annee_service', 'specialite_enseignee') if f in data}

        from apps.users.repositories.user_repository import UserRepository
        if user_fields:
            UserRepository.update(obj.user, **user_fields)
        if profil_fields:
            EnseignantChercheurRepository.update(obj, **profil_fields)

        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=obj.user, details={'champs': list(data.keys())})
        return Response({'success': True, 'message': 'Profil mis à jour.',
                         'data': EnseignantChercheurDetailSerializer(obj).data})

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary='Supprimer un enseignant-chercheur (soft delete)',
        responses={204: OpenApiResponse(description="Compte supprimé.")},
    )
    def delete(self, request, enseignant_id):
        obj, err = self._get_or_404(enseignant_id)
        if err: return err
        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=obj.user)
        EnseignantChercheurRepository.soft_delete(obj)
        return Response({'success': True, 'message': "Compte enseignant-chercheur supprimé.",
                         'data': {}, 'errors': {}}, status=204)


class EnseignantChercheurSuspendreView(APIView):
    """POST /api/enseignants-chercheurs/<id>/suspendre/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(
        tags=['Enseignants-Chercheurs'],
        summary='Suspendre ou réactiver un enseignant-chercheur',
        request=inline_serializer('EnseignantAction', fields={
            'action': s.ChoiceField(choices=['suspendre', 'reactiver'])
        }),
        responses={200: OpenApiResponse(description="Action effectuée.")},
    )
    def post(self, request, enseignant_id):
        action = request.data.get('action')
        if action not in ('suspendre', 'reactiver'):
            return Response({'success': False, 'message': "Action invalide. Valeurs: suspendre | reactiver",
                             'data': {}, 'errors': {}}, status=400)
        if action == 'suspendre':
            result = EnseignantChercheurCreationService.suspendre(str(enseignant_id), request.user)
        else:
            result = EnseignantChercheurCreationService.reactiver(str(enseignant_id), request.user)
        return _resp(result)


# =============================================================================
# 🔬  CHERCHEUR VIEWS (Admin uniquement)
# =============================================================================

class ChercheurCreateView(APIView):
    """POST /api/chercheurs/ — Créer un chercheur [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]
    parser_classes = [JSONParser]

    @extend_schema(
        tags=['Chercheurs'],
        summary='Créer un compte chercheur',
        description="""
## Création d'un compte chercheur

**Réservé à l'administrateur uniquement.**

Le compte est créé actif immédiatement. Un secret TOTP (Google Authenticator) est généré
et retourné dans la réponse — transmettez-le au chercheur pour qu'il configure
son application avant sa première connexion.

## Flux recommandé

```
1. POST /api/chercheurs/                    ← admin crée le compte
2. Transmettre le QR code / secret TOTP au chercheur
3. POST /api/auth/totp/confirm/             ← active le 2FA
4. POST /api/auth/chercheur/login/          ← connexion email + password
5. POST /api/auth/chercheur/totp/verify/    ← vérification TOTP
```
        """,
        request=ChercheurCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Chercheur créé avec succès.",
                response=inline_serializer('ChercheurCreateResponse', fields={
                    'success': s.BooleanField(),
                    'message': s.CharField(),
                    'data': inline_serializer('ChercheurCreateData', fields={
                        'chercheur_id': s.UUIDField(),
                        'user_id': s.UUIDField(),
                        'email': s.EmailField(),
                        'nom_complet': s.CharField(),
                        'user_type': s.CharField(),
                        'statut_compte': s.CharField(),
                        'annee_service': s.IntegerField(allow_null=True),
                        'specialite_enseignee': s.CharField(),
                        'totp_setup': inline_serializer('TOTPSetupCH', fields={
                            'totp_secret': s.CharField(),
                            'qr_uri': s.CharField(),
                            'instructions': s.CharField(),
                        }),
                    }),
                }),
            ),
            400: OpenApiResponse(description="Données invalides."),
            403: OpenApiResponse(description="Réservé à l'administrateur."),
        },
        examples=[
            OpenApiExample(
                'Créer un chercheur',
                request_only=True,
                value={
                    "first_name": "Mariam",
                    "last_name": "DIALLO",
                    "email": "m.diallo@recherche.bf",
                    "phone": "+22670200001",
                    "date_of_birth": "1985-03-22",
                    "password": "Chercheur@2025!",
                    "confirm_password": "Chercheur@2025!",
                    "numero_piece": "CNIB87654321",
                    "lieu_habitation": "Ouagadougou",
                    "annee_service": 2018,
                    "specialite_enseignee": "Biologie Moléculaire",
                },
            ),
        ],
    )
    def post(self, request):
        serializer = ChercheurCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)
        result = ChercheurCreationService.creer(
            data=serializer.validated_data, effectue_par=request.user
        )
        return _resp(result)


class ChercheurListView(APIView):
    """GET /api/chercheurs/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(
        tags=['Chercheurs'],
        summary='Lister les chercheurs',
        parameters=EC_LIST_PARAMETERS,
        responses={200: OpenApiResponse(description="Liste des chercheurs.")},
    )
    def get(self, request):
        qs = _build_chercheur_queryset(request)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = qs.count()
        start = (page - 1) * page_size
        serializer = ChercheurDetailSerializer(qs[start:start + page_size], many=True)
        return Response({
            'success': True, 'count': total, 'page': page,
            'pages': (total + page_size - 1) // page_size,
            'results': serializer.data,
        })


class ChercheurDetailView(APIView):
    """GET/PATCH/DELETE /api/chercheurs/<id>/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]
    parser_classes = [JSONParser]

    def _get_or_404(self, pk):
        obj = ChercheurRepository.get_by_id(pk)
        if not obj:
            return None, Response({'success': False, 'message': "Chercheur introuvable.",
                                   'data': {}, 'errors': {}}, status=404)
        return obj, None

    @extend_schema(
        tags=['Chercheurs'],
        summary="Détail d'un chercheur",
        responses={200: OpenApiResponse(description="Détail.", response=ChercheurDetailSerializer)},
    )
    def get(self, request, chercheur_id):
        obj, err = self._get_or_404(chercheur_id)
        if err: return err
        return Response({'success': True, 'data': ChercheurDetailSerializer(obj).data})

    @extend_schema(
        tags=['Chercheurs'],
        summary='Modifier un chercheur (PATCH)',
        request=ChercheurUpdateSerializer,
        responses={200: OpenApiResponse(description="Profil mis à jour.")},
    )
    def patch(self, request, chercheur_id):
        obj, err = self._get_or_404(chercheur_id)
        if err: return err

        serializer = ChercheurUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'message': 'Données invalides.',
                             'data': {}, 'errors': serializer.errors}, status=400)

        data = serializer.validated_data
        user_fields = {f: data[f] for f in ('first_name', 'last_name', 'phone', 'date_of_birth') if f in data}
        profil_fields = {f: data[f] for f in ('numero_piece', 'lieu_habitation', 'annee_service', 'specialite_enseignee') if f in data}

        from apps.users.repositories.user_repository import UserRepository
        if user_fields:
            UserRepository.update(obj.user, **user_fields)
        if profil_fields:
            ChercheurRepository.update(obj, **profil_fields)

        HAS.log_utilisateur('MODIF', auteur=request.user, cible_user=obj.user, details={'champs': list(data.keys())})
        return Response({'success': True, 'message': 'Profil mis à jour.',
                         'data': ChercheurDetailSerializer(obj).data})

    @extend_schema(
        tags=['Chercheurs'],
        summary='Supprimer un chercheur (soft delete)',
        responses={204: OpenApiResponse(description="Compte supprimé.")},
    )
    def delete(self, request, chercheur_id):
        obj, err = self._get_or_404(chercheur_id)
        if err: return err
        HAS.log_utilisateur('SUPPRIME', auteur=request.user, cible_user=obj.user)
        ChercheurRepository.soft_delete(obj)
        return Response({'success': True, 'message': "Compte chercheur supprimé.",
                         'data': {}, 'errors': {}}, status=204)


class ChercheurSuspendreView(APIView):
    """POST /api/chercheurs/<id>/suspendre/ [Admin]"""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(
        tags=['Chercheurs'],
        summary='Suspendre ou réactiver un chercheur',
        request=inline_serializer('ChercheurAction', fields={
            'action': s.ChoiceField(choices=['suspendre', 'reactiver'])
        }),
        responses={200: OpenApiResponse(description="Action effectuée.")},
    )
    def post(self, request, chercheur_id):
        action = request.data.get('action')
        if action not in ('suspendre', 'reactiver'):
            return Response({'success': False, 'message': "Action invalide. Valeurs: suspendre | reactiver",
                             'data': {}, 'errors': {}}, status=400)
        if action == 'suspendre':
            result = ChercheurCreationService.suspendre(str(chercheur_id), request.user)
        else:
            result = ChercheurCreationService.reactiver(str(chercheur_id), request.user)
        return _resp(result)
