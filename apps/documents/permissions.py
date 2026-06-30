from rest_framework.permissions import BasePermission


class CanManageDocuments(BasePermission):
    message = (
        "Acces reserve aux administrateurs et aux bibliothecaires "
        "autorises a gerer les documents."
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.user_type == "ADMINISTRATEUR":
            return True

        if user.user_type == "BIBLIOTHECAIRE":
            profil = getattr(user, "profil_bibliothecaire", None)
            return bool(profil and profil.peut_gerer_documents)

        return False
