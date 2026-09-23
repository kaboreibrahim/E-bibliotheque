"""
apps/specialites/repositories.py
"""
from django.db.models import Count, QuerySet
from apps.specialites.models import Specialite


class SpecialiteRepository:

    @staticmethod
    def _with_counts(queryset: QuerySet) -> QuerySet:
        """Annote les compteurs (prefixes par _ pour ne pas entrer en conflit
        avec les @property de meme nom sur le modele, cf. Specialite.nb_etudiants)."""
        return queryset.annotate(
            _nb_etudiants=Count("etudiants", distinct=True),
            _nb_documents=Count("documents", distinct=True),
            _nb_ues=Count("ues", distinct=True),
        )

    @staticmethod
    def get_all() -> QuerySet:
        return SpecialiteRepository._with_counts(
            Specialite.objects.select_related("niveau__filiere").all()
        )

    @staticmethod
    def get_by_id(specialite_id: str) -> Specialite | None:
        return (
            SpecialiteRepository._with_counts(
                Specialite.objects.select_related("niveau__filiere")
            )
            .filter(pk=specialite_id)
            .first()
        )

    @staticmethod
    def get_by_niveau(niveau_id: str) -> QuerySet:
        return SpecialiteRepository._with_counts(
            Specialite.objects.select_related("niveau__filiere").filter(niveau_id=niveau_id)
        )

    @staticmethod
    def get_by_name_and_niveau(name: str, niveau_id: str) -> Specialite | None:
        return Specialite.objects.filter(name__iexact=name, niveau_id=niveau_id).first()

    @staticmethod
    def search(q: str) -> QuerySet:
        return SpecialiteRepository._with_counts(
            Specialite.objects
            .select_related("niveau__filiere")
            .filter(name__icontains=q)
        )

    @staticmethod
    def create(name: str, niveau_id: str) -> Specialite:
        return Specialite.objects.create(name=name, niveau_id=niveau_id)

    @staticmethod
    def update(specialite: Specialite, **fields) -> Specialite:
        for attr, value in fields.items():
            setattr(specialite, attr, value)
        specialite.save(update_fields=list(fields.keys()) + ["updated_at"])
        return specialite

    @staticmethod
    def delete(specialite: Specialite) -> None:
        specialite.delete()