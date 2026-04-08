"""
=============================================================================
 apps/users/views/auth_views.py
 APIViews — 3 flux d'authentification séparés avec docs Swagger complètes
=============================================================================
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
)
from rest_framework import serializers as drf_serializers

from apps.users.serializers.auth_serializers import (
    EtudiantLoginSerializer, EtudiantTOTPVerifySerializer,
    BibliothecaireLoginSerializer, BibliothecaireTOTPVerifySerializer,
    AdminLoginSerializer, AdminTOTPVerifySerializer,
    OTPSendSerializer, OTPVerifySerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    TokenRefreshSerializer, LogoutSerializer, TOTPSetupConfirmSerializer,
)
from apps.users.services.auth_service import (
    EtudiantAuthService,
    BibliothecaireAuthService,
    AdminAuthService,
    CommonAuthService,
)
from apps.users.repositories.user_repository import UserRepository


# ── Helper IP/UA ──────────────────────────────────────────────────────────────
def _meta(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    ip  = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
    return {'ip': ip, 'ua': request.META.get('HTTP_USER_AGENT', '')}


def _resp(result):
    return Response(
        {'success': result.success, 'message': result.message,
         'data': result.data or {}, 'errors': result.errors or {}},
        status=result.http_status
    )


# =============================================================================
# 🎓  ÉTUDIANT AUTH
# =============================================================================

class EtudiantLoginView(APIView):
    """
    POST /api/auth/etudiant/login/

    Étape 1 — Connexion étudiant par matricule + mot de passe.
    Si les identifiants sont valides, retourne user_id pour l'étape 2 (TOTP).
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Étudiant'],
        summary='Connexion étudiant (étape 1/2) — Matricule + Mot de passe',
        description="""
## Connexion Étudiant — Étape 1/2

Connexion par **matricule** + **mot de passe**.

### Flux complet :
```
POST /api/auth/etudiant/login/       ← étape 1 (matricule + password)
         ↓  retourne user_id
POST /api/auth/etudiant/totp/verify/ ← étape 2 (code Google Authenticator)
         ↓  retourne access + refresh tokens
```

### Vérifications effectuées :
- Matricule valide (format ETU + année + 5 chiffres)
- Mot de passe correct
- Compte actif (`is_active = True`)
- Compte non expiré (`compte_expire_le` non dépassé)
- Google Authenticator configuré (`is_2fa_enabled = True`)
        """,
        request=EtudiantLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Identifiants valides — TOTP requis",
                response=inline_serializer('EtudiantLoginOK', fields={
                    'success':      drf_serializers.BooleanField(),
                    'message':      drf_serializers.CharField(),
                    'data': inline_serializer('EtudiantLoginData', fields={
                        'requires_totp': drf_serializers.BooleanField(help_text="Toujours True — le TOTP est obligatoire"),
                        'user_id':       drf_serializers.UUIDField(help_text="À passer à l'étape 2"),
                        'user_type':     drf_serializers.CharField(help_text="ETUDIANT"),
                        'nom_complet':   drf_serializers.CharField(help_text="Prénom Nom de l'étudiant"),
                    })
                })
            ),
            401: OpenApiResponse(description="Matricule ou mot de passe incorrect"),
            403: OpenApiResponse(description="Compte désactivé, expiré ou 2FA non configuré"),
        },
        examples=[
            OpenApiExample(
                'Corps de la requête',
                value={'matricule': 'ETU202512345', 'password': 'Etudiant@2025!'},
                request_only=True,
            ),
            OpenApiExample(
                'Réponse succès',
                value={
                    'success': True,
                    'message': 'Identifiants valides. Veuillez saisir votre code Google Authenticator.',
                    'data': {
                        'requires_totp': True,
                        'user_id':       '550e8400-e29b-41d4-a716-446655440000',
                        'user_type':     'ETUDIANT',
                        'nom_complet':   'Inès IRIÉ',
                    },
                    'errors': {}
                },
                response_only=True, status_codes=['200'],
            ),
            OpenApiExample(
                'Réponse erreur — identifiants invalides',
                value={
                    'success': False,
                    'message': 'Matricule ou mot de passe incorrect.',
                    'data':   {},
                    'errors': {'non_field_errors': ['Identifiants invalides.']}
                },
                response_only=True, status_codes=['401'],
            ),
            OpenApiExample(
                'Réponse erreur — compte expiré',
                value={
                    'success': False,
                    'message': 'Votre compte a expiré il y a 5 jours. Contactez la bibliothèque.',
                    'data':   {},
                    'errors': {'compte': ['Compte expiré.']}
                },
                response_only=True, status_codes=['403'],
            ),
        ]
    )
    def post(self, request):
        s = EtudiantLoginSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        m = _meta(request)
        return _resp(EtudiantAuthService.login(
            matricule=s.validated_data['matricule'],
            password=s.validated_data['password'],
            ip=m['ip'], ua=m['ua']
        ))


class EtudiantTOTPVerifyView(APIView):
    """
    POST /api/auth/etudiant/totp/verify/

    Étape 2 — Valide le code Google Authenticator de l'étudiant.
    Retourne les tokens JWT si le code est correct.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Étudiant'],
        summary='Connexion étudiant (étape 2/2) — Code Google Authenticator',
        description="""
## Connexion Étudiant — Étape 2/2

Validation du code **Google Authenticator** (TOTP à 6 chiffres).

> Le `user_id` est retourné à l'étape 1 (`/api/auth/etudiant/login/`).

### En cas de succès :
- Retourne `access` token (valable **15 minutes**)
- Retourne `refresh` token (valable **7 jours**)
- Retourne le profil complet de l'étudiant

### Utilisation des tokens :
```
Authorization: Bearer <access_token>
```
        """,
        request=EtudiantTOTPVerifySerializer,
        responses={
            200: OpenApiResponse(
                description="Connexion réussie — tokens JWT retournés",
                response=inline_serializer('EtudiantTOTPOK', fields={
                    'success': drf_serializers.BooleanField(),
                    'message': drf_serializers.CharField(),
                    'data': inline_serializer('EtudiantTokenData', fields={
                        'access':      drf_serializers.CharField(help_text="JWT Access token — 15 min"),
                        'refresh':     drf_serializers.CharField(help_text="JWT Refresh token — 7 jours"),
                        'user_id':     drf_serializers.UUIDField(),
                        'user_type':   drf_serializers.CharField(help_text="ETUDIANT"),
                        'email':       drf_serializers.EmailField(),
                        'nom_complet': drf_serializers.CharField(),
                        'profil': inline_serializer('EtudiantProfil', fields={
                            'matricule':      drf_serializers.CharField(),
                            'filiere':        drf_serializers.CharField(),
                            'niveau':         drf_serializers.CharField(),
                            'specialite':     drf_serializers.CharField(allow_null=True),
                            'jours_restants': drf_serializers.IntegerField(help_text="Jours avant expiration du compte"),
                            'statut_compte':  drf_serializers.CharField(help_text="✅ Actif (20 jours restants)"),
                        })
                    })
                })
            ),
            400: OpenApiResponse(description="Code TOTP invalide ou expiré"),
            404: OpenApiResponse(description="Étudiant introuvable"),
        },
        examples=[
            OpenApiExample(
                'Corps de la requête',
                value={'user_id': '550e8400-e29b-41d4-a716-446655440000', 'totp_code': '123456'},
                request_only=True,
            ),
            OpenApiExample(
                'Réponse succès',
                value={
                    'success': True, 'message': 'Connexion réussie. Bienvenue !',
                    'data': {
                        'access':      'eyJhbGciOiJIUzI1NiJ9...',
                        'refresh':     'eyJhbGciOiJIUzI1NiJ9...',
                        'user_id':     '550e8400-e29b-41d4-a716-446655440000',
                        'user_type':   'ETUDIANT',
                        'email':       'etu.irie.m2c@etud-ci.edu',
                        'nom_complet': 'Inès IRIÉ',
                        'profil': {
                            'matricule':      'ETU202512345',
                            'filiere':        'Droit des Contentieux',
                            'niveau':         'M2',
                            'specialite':     'Droit des Contentieux',
                            'jours_restants': 20,
                            'statut_compte':  '✅ Actif (20 jours restants)',
                        }
                    }, 'errors': {}
                },
                response_only=True, status_codes=['200'],
            ),
        ]
    )
    def post(self, request):
        s = EtudiantTOTPVerifySerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(EtudiantAuthService.verify_totp(
            user_id=str(s.validated_data['user_id']),
            totp_code=s.validated_data['totp_code'],
            ip=_meta(request)['ip']
        ))


# =============================================================================
# 📖  BIBLIOTHÉCAIRE AUTH
# =============================================================================

class BibliothecaireLoginView(APIView):
    """POST /api/auth/bibliothecaire/login/ — Étape 1"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Bibliothécaire'],
        summary='Connexion bibliothécaire (étape 1/2) — Email + Mot de passe',
        description="""
## Connexion Bibliothécaire — Étape 1/2

Connexion par **email professionnel** + **mot de passe**.

### Flux complet :
```
POST /api/auth/bibliothecaire/login/       ← étape 1
POST /api/auth/bibliothecaire/totp/verify/ ← étape 2 (TOTP obligatoire)
```
        """,
        request=BibliothecaireLoginSerializer,
        responses={
            200: OpenApiResponse(description="Identifiants valides — TOTP requis"),
            401: OpenApiResponse(description="Email ou mot de passe incorrect"),
            403: OpenApiResponse(description="Compte désactivé ou TOTP non configuré"),
        },
        examples=[
            OpenApiExample(
                'Requête', request_only=True,
                value={'email': 'biblio.kone@universite-ci.edu', 'password': 'Biblio@2025!'}
            ),
            OpenApiExample(
                'Succès', response_only=True, status_codes=['200'],
                value={
                    'success': True,
                    'message': 'Identifiants valides. Veuillez saisir votre code Google Authenticator.',
                    'data': {
                        'requires_totp': True,
                        'user_id':       '661e8400-e29b-41d4-a716-446655440111',
                        'user_type':     'BIBLIOTHECAIRE',
                        'nom_complet':   'Mariam KONÉ',
                    }, 'errors': {}
                }
            ),
        ]
    )
    def post(self, request):
        s = BibliothecaireLoginSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        m = _meta(request)
        return _resp(BibliothecaireAuthService.login(
            email=s.validated_data['email'],
            password=s.validated_data['password'],
            ip=m['ip'], ua=m['ua']
        ))


class BibliothecaireTOTPVerifyView(APIView):
    """POST /api/auth/bibliothecaire/totp/verify/ — Étape 2"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Bibliothécaire'],
        summary='Connexion bibliothécaire (étape 2/2) — Code Google Authenticator',
        description="Valide le code TOTP et retourne les tokens JWT avec les permissions du bibliothécaire.",
        request=BibliothecaireTOTPVerifySerializer,
        responses={
            200: OpenApiResponse(
                description="Connexion réussie",
                response=inline_serializer('BibliothecaireTOTPOK', fields={
                    'success': drf_serializers.BooleanField(),
                    'data': inline_serializer('BibliothecaireTokenData', fields={
                        'access':      drf_serializers.CharField(),
                        'refresh':     drf_serializers.CharField(),
                        'user_type':   drf_serializers.CharField(help_text="BIBLIOTHECAIRE"),
                        'nom_complet': drf_serializers.CharField(),
                        'permissions': inline_serializer('BiblioPerms', fields={
                            'peut_gerer_documents':    drf_serializers.BooleanField(),
                            'peut_gerer_utilisateurs': drf_serializers.BooleanField(),
                            'badge_number':            drf_serializers.CharField(),
                        })
                    })
                })
            ),
            400: OpenApiResponse(description="Code TOTP invalide"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True,
                value={'user_id': '661e8400-e29b-41d4-a716-446655440111', 'totp_code': '654321'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={
                    'success': True, 'message': 'Connexion réussie.',
                    'data': {
                        'access': 'eyJhbGciOiJIUzI1NiJ9...', 'refresh': 'eyJhbGciOiJIUzI1NiJ9...',
                        'user_type': 'BIBLIOTHECAIRE', 'email': 'biblio.kone@universite-ci.edu',
                        'nom_complet': 'Mariam KONÉ',
                        'permissions': {
                            'peut_gerer_documents': True,
                            'peut_gerer_utilisateurs': True,
                            'badge_number': 'BIB-2025-001'
                        }
                    }, 'errors': {}
                }),
        ]
    )
    def post(self, request):
        s = BibliothecaireTOTPVerifySerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(BibliothecaireAuthService.verify_totp(
            user_id=str(s.validated_data['user_id']),
            totp_code=s.validated_data['totp_code'],
            ip=_meta(request)['ip']
        ))


# =============================================================================
# 🔑  ADMIN AUTH
# =============================================================================

class AdminLoginView(APIView):
    """POST /api/auth/admin/login/ — Étape 1"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Administrateur'],
        summary='Connexion administrateur (étape 1/2) — Email + Mot de passe',
        description="""
## Connexion Administrateur — Étape 1/2

Connexion par **email** + **mot de passe**.

### Flux :
```
POST /api/auth/admin/login/        ← étape 1
POST /api/auth/admin/totp/verify/  ← étape 2 (TOTP obligatoire)
```
        """,
        request=AdminLoginSerializer,
        responses={
            200: OpenApiResponse(description="Identifiants valides — TOTP requis"),
            401: OpenApiResponse(description="Email ou mot de passe incorrect"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True,
                value={'email': 'admin@universite-ci.edu', 'password': 'Admin@2025!'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={
                    'success': True,
                    'message': 'Identifiants valides. Veuillez saisir votre code Google Authenticator.',
                    'data': {
                        'requires_totp': True,
                        'user_id':   '772e8400-e29b-41d4-a716-446655440222',
                        'user_type': 'ADMINISTRATEUR',
                        'nom_complet': 'Kouamé BROU',
                    }, 'errors': {}
                }),
        ]
    )
    def post(self, request):
        s = AdminLoginSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        m = _meta(request)
        return _resp(AdminAuthService.login(
            email=s.validated_data['email'],
            password=s.validated_data['password'],
            ip=m['ip'], ua=m['ua']
        ))


class AdminTOTPVerifyView(APIView):
    """POST /api/auth/admin/totp/verify/ — Étape 2"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Administrateur'],
        summary='Connexion administrateur (étape 2/2) — Code Google Authenticator',
        request=AdminTOTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="Connexion admin réussie — tokens JWT"),
            400: OpenApiResponse(description="Code TOTP invalide"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True,
                value={'user_id': '772e8400-e29b-41d4-a716-446655440222', 'totp_code': '789012'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={
                    'success': True, 'message': 'Connexion administrateur réussie.',
                    'data': {
                        'access': 'eyJhbGciOiJIUzI1NiJ9...', 'refresh': 'eyJhbGciOiJIUzI1NiJ9...',
                        'user_type': 'ADMINISTRATEUR', 'email': 'admin@universite-ci.edu',
                        'nom_complet': 'Kouamé BROU', 'is_superuser': True,
                    }, 'errors': {}
                }),
        ]
    )
    def post(self, request):
        s = AdminTOTPVerifySerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(AdminAuthService.verify_totp(
            user_id=str(s.validated_data['user_id']),
            totp_code=s.validated_data['totp_code'],
            ip=_meta(request)['ip']
        ))


# =============================================================================
# 🔧  TOTP SETUP (commun Admin + Biblio)
# =============================================================================

class TOTPSetupView(APIView):
    """GET /api/auth/totp/setup/ — Génère QR code Google Authenticator"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth — Configuration 2FA'],
        summary='Configurer Google Authenticator — Obtenir le QR code',
        description="""
## Configuration Google Authenticator

Génère un **secret TOTP** et un **QR code URI** à scanner avec Google Authenticator.

**Réservé aux Admin et Bibliothécaires.**

Après avoir scanné, confirmez avec `/api/auth/totp/confirm/`.
        """,
        responses={
            200: OpenApiResponse(
                description="Secret TOTP et QR code URI générés",
                response=inline_serializer('TOTPSetupResponse', fields={
                    'data': inline_serializer('TOTPSetupData', fields={
                        'totp_secret':  drf_serializers.CharField(help_text="Secret base32 à saisir manuellement si scan impossible"),
                        'qr_uri':       drf_serializers.CharField(help_text="URI à encoder en QR code côté frontend"),
                        'qr_code_base64': drf_serializers.CharField(help_text="Image QR encodée en base64, prête à afficher"),
                        'instructions': drf_serializers.ListField(child=drf_serializers.CharField()),
                    })
                })
            ),
            403: OpenApiResponse(description="Réservé aux Admin et Bibliothécaires"),
        },
        examples=[
            OpenApiExample('Réponse', response_only=True, status_codes=['200'],
                value={
                    'success': True,
                    'message': 'Scannez ce QR code avec Google Authenticator.',
                    'data': {
                        'totp_secret': 'JBSWY3DPEHPK3PXP',
                        'qr_uri':      'otpauth://totp/Biblioth%C3%A8que%20Universitaire%20CI:admin%40universite-ci.edu?secret=JBSWY3DPEHPK3PXP&issuer=Biblioth%C3%A8que+Universitaire+CI',
                        'qr_code_base64': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...',
                        'instructions': [
                            '1. Ouvrez Google Authenticator sur votre téléphone.',
                            "2. Appuyez sur '+' puis 'Scanner un QR code'.",
                            '3. Scannez le QR code ou entrez le secret manuellement.',
                            '4. Confirmez avec le code généré sur /totp/confirm/.',
                        ]
                    }, 'errors': {}
                }),
        ]
    )
    def get(self, request):
        if not request.user.requires_2fa:
            return Response({'success': False, 'message': 'Réservé aux Admin et Bibliothécaires.'}, status=403)
        return _resp(CommonAuthService.setup_totp(request.user))


class TOTPConfirmView(APIView):
    """POST /api/auth/totp/confirm/ — Active le 2FA après scan QR code"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Configuration 2FA'],
        summary='Confirmer la configuration Google Authenticator',
        description=(
            "Valide le premier code TOTP après scan du QR code. "
            "Fonctionne soit avec une session authentifiee, soit avec le "
            "`setup_token` retourne lors d'une premiere connexion."
        ),
        request=TOTPSetupConfirmSerializer,
        responses={
            200: OpenApiResponse(description="2FA activé avec succès"),
            400: OpenApiResponse(description="Code invalide"),
        },
        examples=[
            OpenApiExample('Requête authentifiée', request_only=True, value={'totp_code': '123456'}),
            OpenApiExample(
                'Requête première connexion',
                request_only=True,
                value={'setup_token': 'eyJ1c2VyX2lkIjoiLi4uIn0:1abcde:signature', 'totp_code': '123456'}
            ),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={'success': True,
                    'message': 'Google Authenticator activé avec succès ! Le 2FA est maintenant actif.',
                    'data': {}, 'errors': {}}),
        ]
    )
    def post(self, request):
        s = TOTPSetupConfirmSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        meta = _meta(request)
        if request.user.is_authenticated:
            return _resp(CommonAuthService.confirm_totp_setup(
                request.user,
                s.validated_data['totp_code'],
                ip=meta['ip'],
            ))

        setup_token = s.validated_data.get('setup_token')
        if not setup_token:
            return Response({
                'success': False,
                'message': "Le champ 'setup_token' est requis sans session authentifiée.",
                'data': {},
                'errors': {'setup_token': ['Champ requis.']},
            }, status=400)

        return _resp(CommonAuthService.confirm_totp_setup_with_token(
            setup_token=setup_token,
            totp_code=s.validated_data['totp_code'],
            ip=meta['ip'],
        ))


# =============================================================================
# 📧  OTP EMAIL (commun)
# =============================================================================

class OTPSendView(APIView):
    """POST /api/auth/otp/send/ — Envoie un code OTP par email"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — OTP Email'],
        summary='Envoyer un code OTP par email',
        description="""
Génère et envoie un code OTP à 6 chiffres par email.

| type_code       | Usage                                   |
|-----------------|-----------------------------------------|
| `activation`    | Activer un nouveau compte               |
| `password_reset`| Réinitialiser le mot de passe           |
| `email_change`  | Confirmer un changement d'email         |
| `code_OTP`      | 2FA email (usage interne uniquement)    |

**Limite anti-spam :** max 3 codes en 10 minutes.
        """,
        request=OTPSendSerializer,
        responses={
            200: OpenApiResponse(description="OTP envoyé"),
            429: OpenApiResponse(description="Trop de tentatives — attendez 10 min"),
        },
        examples=[
            OpenApiExample('Reset password', request_only=True,
                value={'type_code': 'password_reset', 'email': 'user@universite-ci.edu'}),
            OpenApiExample('Activation compte', request_only=True,
                value={'type_code': 'activation'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={
                    'success': True, 'message': "Code OTP envoyé à user@universite-ci.edu. Valable 3 minutes.",
                    'data': {'email': 'user@universite-ci.edu', 'expires_in_seconds': 180}, 'errors': {}
                }),
        ]
    )
    def post(self, request):
        s = OTPSendSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)

        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            email = s.validated_data.get('email') or request.data.get('email')
            if email:
                user = UserRepository.get_by_email(email)

        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable.", 'data': {}, 'errors': {}}, status=404)

        return _resp(CommonAuthService.send_otp(user, s.validated_data['type_code'], s.validated_data.get('email')))


class OTPVerifyView(APIView):
    """POST /api/auth/otp/verify/ — Vérifie un code OTP email"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — OTP Email'],
        summary='Vérifier un code OTP email',
        request=OTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="OTP valide"),
            400: OpenApiResponse(description="Code invalide, expiré ou tentatives épuisées"),
        },
        examples=[
            OpenApiExample('Vérification reset', request_only=True,
                value={'code': '654321', 'type_code': 'password_reset', 'email': 'user@universite-ci.edu'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={'success': True, 'message': 'Code OTP vérifié avec succès.',
                    'data': {'type_code': 'password_reset', 'verified': True}, 'errors': {}}),
        ]
    )
    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)

        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            email = s.validated_data.get('email') or request.data.get('email')
            if email:
                user = UserRepository.get_by_email(email)

        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable.", 'data': {}, 'errors': {}}, status=404)

        return _resp(CommonAuthService.verify_otp(user, s.validated_data['type_code'], s.validated_data['code'], _meta(request)['ip']))


# =============================================================================
# 🔄  RESET PASSWORD
# =============================================================================

class PasswordResetRequestView(APIView):
    """POST /api/auth/password/reset/ — Demande reset mot de passe"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Mot de passe'],
        summary='Demander la réinitialisation du mot de passe',
        description="Envoie un code OTP par email. **Réponse générique** pour éviter l'énumération des comptes.",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Réponse générique (sécurité)")},
        examples=[
            OpenApiExample('Requête', request_only=True, value={'email': 'user@universite-ci.edu'}),
            OpenApiExample('Réponse', response_only=True, status_codes=['200'],
                value={'success': True, 'message': "Si un compte existe avec cet email, un code a été envoyé.",
                    'data': {}, 'errors': {}}),
        ]
    )
    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        user = UserRepository.get_by_email(s.validated_data['email'])
        if user and user.is_active:
            CommonAuthService.send_otp(user=user, type_code='password_reset')
        return Response({'success': True, 'message': "Si un compte existe avec cet email, un code a été envoyé.", 'data': {}, 'errors': {}})


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password/reset/confirm/ — Nouveau mot de passe après OTP"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Mot de passe'],
        summary='Confirmer le nouveau mot de passe',
        description="Définit le nouveau mot de passe. L'OTP `password_reset` doit avoir été vérifié avant.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Mot de passe réinitialisé"),
            400: OpenApiResponse(description="Mots de passe ne correspondent pas / règles non respectées"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True,
                value={'email': 'user@universite-ci.edu', 'new_password': 'NouveauPass@2025!', 'confirm_password': 'NouveauPass@2025!'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={'success': True, 'message': 'Mot de passe réinitialisé. Reconnectez-vous.', 'data': {}, 'errors': {}}),
        ]
    )
    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(CommonAuthService.reset_password(s.validated_data['email'], s.validated_data['new_password']))


# =============================================================================
# 🔄  TOKEN REFRESH + LOGOUT
# =============================================================================

class TokenRefreshView(APIView):
    """POST /api/auth/token/refresh/ — Rafraîchit l'access token"""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth — Tokens JWT'],
        summary='Rafraîchir le token d\'accès JWT',
        description="Génère un nouvel `access` token. L'ancien `refresh` est révoqué (rotation automatique).",
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(description="Nouveaux tokens"),
            401: OpenApiResponse(description="Refresh token invalide ou expiré"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True, value={'refresh': 'eyJhbGciOiJIUzI1NiJ9...'}),
            OpenApiExample('Succès', response_only=True, status_codes=['200'],
                value={'success': True, 'message': 'Token rafraîchi.',
                    'data': {'access': 'eyJhbGciOiJIUzI1NiJ9...nouveau', 'refresh': 'eyJhbGciOiJIUzI1NiJ9...nouveau'},
                    'errors': {}}),
        ]
    )
    def post(self, request):
        s = TokenRefreshSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(CommonAuthService.refresh_token(s.validated_data['refresh']))


class LogoutView(APIView):
    """POST /api/auth/logout/ — Déconnexion"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth — Tokens JWT'],
        summary='Déconnexion — Révoquer le refresh token',
        description=(
            "Révoque le refresh token du compte authentifié et l'ajoute à la "
            "blacklist. L'access token expire naturellement."
        ),
        request=LogoutSerializer,
        responses={
            205: OpenApiResponse(description="Déconnecté avec succès"),
            400: OpenApiResponse(description="Token invalide ou déjà révoqué"),
        },
        examples=[
            OpenApiExample('Requête', request_only=True, value={'refresh': 'eyJhbGciOiJIUzI1NiJ9...'}),
            OpenApiExample('Succès', response_only=True, status_codes=['205'],
                value={'success': True, 'message': 'Déconnexion réussie.', 'data': {}, 'errors': {}}),
        ]
    )
    def post(self, request):
        s = LogoutSerializer(data=request.data)
        if not s.is_valid():
            return Response({'success': False, 'errors': s.errors, 'data': {}, 'message': 'Données invalides.'}, status=400)
        return _resp(CommonAuthService.logout(request.user, s.validated_data['refresh'], _meta(request)['ip']))
