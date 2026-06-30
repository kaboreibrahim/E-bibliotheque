from django.db.models import QuerySet

from apps.users.models import PersonneExterne, EnseignantChercheur, Chercheur, User


class PersonneExterneRepository:
    @staticmethod
    def get_by_id(personne_id: str) -> PersonneExterne | None:
        try:
            return PersonneExterne.objects.select_related("user").get(id=personne_id)
        except PersonneExterne.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> PersonneExterne | None:
        try:
            return PersonneExterne.objects.select_related("user").get(user=user)
        except PersonneExterne.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: dict | None = None) -> QuerySet:
        queryset = PersonneExterne.objects.select_related("user").all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset.order_by("user__last_name", "user__first_name")

    @staticmethod
    def create(user: User) -> PersonneExterne:
        return PersonneExterne.objects.create(user=user)

    @staticmethod
    def update(personne: PersonneExterne, **fields) -> PersonneExterne:
        for key, value in fields.items():
            setattr(personne, key, value)
        personne.save(update_fields=list(fields.keys()) + ["updated_at"])
        return personne

    @staticmethod
    def soft_delete(personne: PersonneExterne) -> None:
        personne.delete()

    @staticmethod
    def activer(personne: PersonneExterne) -> PersonneExterne:
        personne.activer_compte()
        return personne

    @staticmethod
    def desactiver(personne: PersonneExterne, manuel: bool = True) -> None:
        personne.desactiver_compte(manuel=manuel)


# =============================================================================
# 👨‍🏫  ENSEIGNANT-CHERCHEUR REPOSITORY
# =============================================================================

class EnseignantChercheurRepository:

    @staticmethod
    def get_by_id(pk: str) -> EnseignantChercheur | None:
        try:
            return EnseignantChercheur.objects.select_related("user").get(id=pk)
        except EnseignantChercheur.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> EnseignantChercheur | None:
        try:
            return EnseignantChercheur.objects.select_related("user").get(user=user)
        except EnseignantChercheur.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: dict | None = None) -> QuerySet:
        qs = EnseignantChercheur.objects.select_related("user").all()
        if filters:
            qs = qs.filter(**filters)
        return qs.order_by("user__last_name", "user__first_name")

    @staticmethod
    def create(user: User, **fields) -> EnseignantChercheur:
        return EnseignantChercheur.objects.create(user=user, **fields)

    @staticmethod
    def update(obj: EnseignantChercheur, **fields) -> EnseignantChercheur:
        for key, value in fields.items():
            setattr(obj, key, value)
        obj.save(update_fields=list(fields.keys()) + ["updated_at"])
        return obj

    @staticmethod
    def suspendre(obj: EnseignantChercheur) -> EnseignantChercheur:
        obj.suspendre_compte()
        return obj

    @staticmethod
    def reactiver(obj: EnseignantChercheur) -> EnseignantChercheur:
        obj.reactiver_compte()
        return obj

    @staticmethod
    def soft_delete(obj: EnseignantChercheur) -> None:
        obj.delete()


# =============================================================================
# 🔬  CHERCHEUR REPOSITORY
# =============================================================================

class ChercheurRepository:

    @staticmethod
    def get_by_id(pk: str) -> Chercheur | None:
        try:
            return Chercheur.objects.select_related("user").get(id=pk)
        except Chercheur.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> Chercheur | None:
        try:
            return Chercheur.objects.select_related("user").get(user=user)
        except Chercheur.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: dict | None = None) -> QuerySet:
        qs = Chercheur.objects.select_related("user").all()
        if filters:
            qs = qs.filter(**filters)
        return qs.order_by("user__last_name", "user__first_name")

    @staticmethod
    def create(user: User, **fields) -> Chercheur:
        return Chercheur.objects.create(user=user, **fields)

    @staticmethod
    def update(obj: Chercheur, **fields) -> Chercheur:
        for key, value in fields.items():
            setattr(obj, key, value)
        obj.save(update_fields=list(fields.keys()) + ["updated_at"])
        return obj

    @staticmethod
    def suspendre(obj: Chercheur) -> Chercheur:
        obj.suspendre_compte()
        return obj

    @staticmethod
    def reactiver(obj: Chercheur) -> Chercheur:
        obj.reactiver_compte()
        return obj

    @staticmethod
    def soft_delete(obj: Chercheur) -> None:
        obj.delete()
