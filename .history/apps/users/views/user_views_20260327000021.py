"""
=============================================================================
 apps/users/views/user_views.py
 COUCHE VUE — APIViews DRF pour la gestion des utilisateurs
=============================================================================
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser
from drf_spectacular.utils import extend_schema

from apps.users.serializers.serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)
from apps.users.services.user_service import UserService
from apps.users.repositories.user_repository import UserRepository
from apps.users.permissions import (
    IsAdministrateur,
    IsAdminOrBibliothecaire,
    IsOwnerOrAdmin,
    IsOwnerOrAdminOrBibliothecaire,
)


# =============================================================================
# 👥  LISTE + CRÉATION
# =============================================================================

class UserListCreateView(APIView):
    """
    GET  /api/users/         → Liste tous les utilisateurs  [Admin]
    POST /api/users/         → Crée un utilisateur          [Admin]
    """
    parser_classes = [JSONParser, MultiPartParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsAdminOrBibliothecaire()]
        return [IsAuthenticated(), IsAdministrateur()]

    @extend_schema(tags=['Utilisateurs'], summary='Lister les utilisateurs')
    def get(self, request):
        filters = {}
        user_type = request.query_params.get('user_type')
        is_active = request.query_params.get('is_active')
        search    = request.query_params.get('search')

        if user_type:
            filters['user_type'] = user_type.upper()
        if is_active is not None:
            filters['is_active'] = is_active.lower() == 'true'

        qs = UserRepository.get_all(filters)

        # Recherche par email / nom / matricule
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        # Pagination simple
        page      = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total     = qs.count()
        start     = (page - 1) * page_size
        end       = start + page_size

        serializer = UserListSerializer(qs[start:end], many=True)
        return Response({
            'success': True,
            'count':   total,
            'page':    page,
            'pages':   (total + page_size - 1) // page_size,
            'results': serializer.data
        })

    @extend_schema(tags=['Utilisateurs'], summary='Créer un utilisateur', request=UserCreateSerializer)
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        data   = serializer.validated_data
        result = UserService.create_user(
            email        = data['email'],
            password     = data['password'],
            first_name   = data['first_name'],
            last_name    = data['last_name'],
            phone        = data['phone'],
            user_type    = data['user_type'],
            effectue_par = request.user,
            date_of_birth= data.get('date_of_birth'),
            avatar       = data.get('avatar'),
        )

        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )


# =============================================================================
# 👤  DÉTAIL + MODIFICATION + SUPPRESSION
# =============================================================================

class UserDetailView(APIView):
    """
    GET    /api/users/<id>/   → Détail        [Owner | Admin | Biblio]
    PATCH  /api/users/<id>/   → Modification  [Owner | Admin]
    DELETE /api/users/<id>/   → Suppression   [Admin]
    """
    parser_classes = [JSONParser, MultiPartParser]

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdministrateur()]
        return [IsAuthenticated(), IsOwnerOrAdminOrBibliothecaire()]

    def _get_user_or_404(self, user_id):
        user = UserRepository.get_by_id(user_id)
        if not user:
            return None
        return user

    @extend_schema(tags=['Utilisateurs'], summary='Détail d\'un utilisateur')
    def get(self, request, user_id):
        user = self._get_user_or_404(user_id)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        # Vérifier la permission objet
        perm = IsOwnerOrAdminOrBibliothecaire()
        if not perm.has_object_permission(request, self, user):
            return Response({'success': False, 'message': perm.message}, status=403)

        serializer = UserDetailSerializer(user)
        return Response({'success': True, 'data': serializer.data})

    @extend_schema(tags=['Utilisateurs'], summary='Modifier un utilisateur', request=UserUpdateSerializer)
    def patch(self, request, user_id):
        user = self._get_user_or_404(user_id)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        perm = IsOwnerOrAdmin()
        if not perm.has_object_permission(request, self, user):
            return Response({'success': False, 'message': perm.message}, status=403)

        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        result = UserService.update_user(
            user         = user,
            fields       = serializer.validated_data,
            effectue_par = request.user,
        )
        return Response(
            {'success': result.success, 'message': result.message,
             'data': result.data, 'errors': result.errors},
            status=result.http_status
        )

    @extend_schema(tags=['Utilisateurs'], summary='Supprimer un utilisateur')
    def delete(self, request, user_id):
        user = self._get_user_or_404(user_id)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        if user == request.user:
            return Response(
                {'success': False, 'message': "Vous ne pouvez pas supprimer votre propre compte."},
                status=400
            )

        result = UserService.delete_user(user=user, effectue_par=request.user)
        return Response({'success': result.success, 'message': result.message}, status=result.http_status)


# =============================================================================
# 👤  MON PROFIL
# =============================================================================

class MeView(APIView):
    """
    GET   /api/users/me/   → Mon profil complet
    PATCH /api/users/me/   → Modifier mon profil
    """
    permission_classes = [IsAuthenticated]
    parser_classes     = [JSONParser, MultiPartParser]

    @extend_schema(tags=['Utilisateurs'], summary='Mon profil')
    def get(self, request):
        result = UserService.get_profile(request.user)
        return Response({'success': True, 'data': result.data})

    @extend_schema(tags=['Utilisateurs'], summary='Modifier mon profil', request=UserUpdateSerializer)
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        result = UserService.update_user(
            user         = request.user,
            fields       = serializer.validated_data,
            effectue_par = request.user,
        )
        return Response(
            {'success': result.success, 'message': result.message},
            status=result.http_status
        )


# =============================================================================
# 🔒  CHANGER MON MOT DE PASSE
# =============================================================================

class ChangePasswordView(APIView):
    """
    POST /api/users/me/password/

    Change le mot de passe de l'utilisateur connecté.
    Requiert l'ancien mot de passe.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Utilisateurs'], summary='Changer mon mot de passe', request=ChangePasswordSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'success': False, 'errors': {'old_password': ['Mot de passe actuel incorrect.']}},
                status=400
            )

        from apps.users.repositories.user_repository import UserRepository
        UserRepository.update_password(user, serializer.validated_data['new_password'])

        return Response({'success': True, 'message': "Mot de passe modifié avec succès."})


# =============================================================================
# 🚫  ACTIVER / DÉSACTIVER UN COMPTE
# =============================================================================

class UserActivateView(APIView):
    """
    POST /api/users/<id>/activate/    → Activer   [Admin | Biblio]
    POST /api/users/<id>/deactivate/  → Désactiver [Admin]
    """
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(tags=['Utilisateurs'], summary='Activer un compte')
    def post(self, request, user_id):
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        from apps.users.repositories.user_repository import UserRepository as UR
        UR.activate(user)
        return Response({'success': True, 'message': f"Compte de {user.get_full_name()} activé."})


class UserDeactivateView(APIView):
    """Désactiver un compte utilisateur."""
    permission_classes = [IsAuthenticated, IsAdministrateur]

    @extend_schema(tags=['Utilisateurs'], summary='Désactiver un compte')
    def post(self, request, user_id):
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response({'success': False, 'message': "Utilisateur introuvable."}, status=404)

        result = UserService.deactivate_user(user=user, effectue_par=request.user)
        return Response(
            {'success': result.success, 'message': result.message},
            status=result.http_status
        )