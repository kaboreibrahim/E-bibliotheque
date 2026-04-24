from django.db.models import QuerySet

from apps.users.models import PersonneExterne, User


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
