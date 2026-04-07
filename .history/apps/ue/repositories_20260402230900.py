"""
apps/ue/repositories.py
"""
from decimal import Decimal
from django.db.models import QuerySet
from apps.ue.models import UE, ECUE


# =============================================================================
# UE
# =============================================================================

class UERepository:

    @staticmethod
    def get_all() -> QuerySet:
        return UE.objects.prefetch_related("niveaux", "ecues").all()

    @staticmethod
    def get_by_id(ue_id: str) -> UE | None:
        return UE.objects.prefetch_related("niveaux", "ecues").filter(pk=ue_id).first()

    @staticmethod
    def get_by_code(code: str) -> UE | None:
        return UE.objects.filter(code__iexact=code).first()

    @staticmethod
    def get_by_niveau(niveau_id: str) -> QuerySet:
        return UE.objects.prefetch_related("niveaux", "ecues").filter(niveaux__id=niveau_id)

    @staticmethod
    def search(q: str) -> QuerySet:
        return UE.objects.prefetch_related("niveaux", "ecues").filter(
            models_Q := None
        )

    @staticmethod
    def search_by_name_or_code(q: str) -> QuerySet:
        from django.db.models import Q
        return UE.objects.prefetch_related("niveaux", "ecues").filter(
            Q(name__icontains=q) | Q(code__icontains=q)
        )

    @staticmethod
    def create(code: str, name: str, niveau_ids: list[str]) -> UE:
        ue = UE.objects.create(code=code, name=name)
        if niveau_ids:
            ue.niveaux.set(niveau_ids)
        return ue

    @staticmethod
    def update(ue: UE, **fields) -> UE:
        niveau_ids = fields.pop("niveau_ids", None)
        for attr, value in fields.items():
            setattr(ue, attr, value)
        ue.save(update_fields=list(fields.keys()))
        if niveau_ids is not None:
            ue.niveaux.set(niveau_ids)
        return ue

    @staticmethod
    def delete(ue: UE) -> None:
        ue.delete()


# =============================================================================
# ECUE
# =============================================================================

class ECUERepository:

    @staticmethod
    def get_all() -> QuerySet:
        return ECUE.objects.select_related("ue").all()

    @staticmethod
    def get_by_id(ecue_id: str) -> ECUE | None:
        return ECUE.objects.select_related("ue").filter(pk=ecue_id).first()

    @staticmethod
    def get_by_ue(ue_id: str) -> QuerySet:
        return ECUE.objects.select_related("ue").filter(ue_id=ue_id)

    @staticmethod
    def get_by_code_and_ue(code: str, ue_id: str) -> ECUE | None:
        return ECUE.objects.filter(code__iexact=code, ue_id=ue_id).first()

    @staticmethod
    def create(ue_id: str, code: str, name: str, coef: Decimal) -> ECUE:
        return ECUE.objects.create(ue_id=ue_id, code=code, name=name, coef=coef)

    @staticmethod
    def update(ecue: ECUE, **fields) -> ECUE:
        for attr, value in fields.items():
            setattr(ecue, attr, value)
        ecue.save(update_fields=list(fields.keys()) + ["updated_at"])
        return ecue

    @staticmethod
    def delete(ecue: ECUE) -> None:
        ecue.delete()