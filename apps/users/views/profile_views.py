from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.history.models import HistoriqueActionService as HAS
from apps.users.serializers.profile_serializers import (
    UserOwnProfileSerializer,
    UserOwnProfileUpdateSerializer,
)


PROFILE_RESPONSE = inline_serializer(
    'UserOwnProfileEnvelope',
    fields={
        'success': s.BooleanField(),
        'message': s.CharField(),
        'data': UserOwnProfileSerializer(),
        'errors': s.DictField(required=False),
    },
)


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(
        tags=['Utilisateurs'],
        summary='Consulter mon profil',
        description=(
            "Retourne le profil de l'utilisateur connecte avec une section "
            "specifique selon son role."
        ),
        responses={
            200: OpenApiResponse(
                description='Profil recupere avec succes.',
                response=PROFILE_RESPONSE,
            ),
        },
    )
    def get(self, request):
        serializer = UserOwnProfileSerializer(
            request.user,
            context={'request': request},
        )
        return Response({
            'success': True,
            'message': 'Profil recupere avec succes.',
            'data': serializer.data,
            'errors': {},
        })

    @extend_schema(
        tags=['Utilisateurs'],
        summary='Mettre a jour ma photo et ma date de naissance',
        description=(
            "Permet a l'etudiant, au bibliothecaire et a l'administrateur "
            "de modifier leur photo de profil et/ou leur date de naissance."
        ),
        request=UserOwnProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description='Profil mis a jour avec succes.',
                response=PROFILE_RESPONSE,
            ),
            400: OpenApiResponse(description='Donnees invalides.'),
        },
        examples=[
            OpenApiExample(
                'Mettre a jour la date de naissance',
                request_only=True,
                value={'date_of_birth': '2001-05-14'},
            ),
            OpenApiExample(
                'Supprimer la photo',
                request_only=True,
                value={'avatar': None},
            ),
        ],
    )
    def patch(self, request):
        serializer = UserOwnProfileUpdateSerializer(
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Donnees invalides.',
                'data': {},
                'errors': serializer.errors,
            }, status=400)

        user = request.user
        data = serializer.validated_data
        updated_fields = []
        previous_avatar_name = user.avatar.name if user.avatar else None
        avatar_storage = user.avatar.storage if user.avatar else None

        if 'date_of_birth' in data:
            user.date_of_birth = data['date_of_birth']
            updated_fields.append('date_of_birth')

        if 'avatar' in data:
            if data['avatar'] is None and user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
            else:
                user.avatar = data['avatar']
            updated_fields.append('avatar')

        user.save(update_fields=updated_fields + ['updated_at'])

        if (
            previous_avatar_name
            and user.avatar
            and avatar_storage is not None
            and previous_avatar_name != user.avatar.name
        ):
            avatar_storage.delete(previous_avatar_name)

        HAS.log_utilisateur(
            'MODIF',
            auteur=user,
            cible_user=user,
            details={'champs': updated_fields, 'source': 'self_profile'},
        )

        profile_serializer = UserOwnProfileSerializer(
            user,
            context={'request': request},
        )
        return Response({
            'success': True,
            'message': 'Profil mis a jour avec succes.',
            'data': profile_serializer.data,
            'errors': {},
        })
