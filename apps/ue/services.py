"""
apps/ue/services.py
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.specialites.repositories import SpecialiteRepository
from apps.ue.models import ECUE, UE
from apps.ue.repositories import ECUERepository, UERepository


# =============================================================================
# UE
# =============================================================================


class UEService:

    def __init__(
        self,
        repo: UERepository | None = None,
        specialite_repo: SpecialiteRepository | None = None,
    ):
        self.repo = repo or UERepository()
        self.specialite_repo = specialite_repo or SpecialiteRepository()

    def list_ues(self, specialite_id: str | None = None, q: str | None = None):
        if q:
            return self.repo.search_by_name_or_code(q)
        if specialite_id:
            return self.repo.get_by_specialite(specialite_id)
        return self.repo.get_all()

    def get_ue(self, ue_id: str) -> UE:
        ue = self.repo.get_by_id(ue_id)
        if not ue:
            raise ValidationError(f"UE introuvable : {ue_id}.")
        return ue

    def _validate_specialite_ids(self, specialite_ids: list[str]) -> None:
        for specialite_id in specialite_ids:
            if not self.specialite_repo.get_by_id(specialite_id):
                raise ValidationError(f"Specialite introuvable : {specialite_id}.")

    def create_ue(self, code: str, name: str, specialite_ids: list[str]) -> UE:
        code = code.strip().upper()
        name = name.strip()
        if not code or not name:
            raise ValidationError("Le code et l'intitule de l'UE sont obligatoires.")
        if self.repo.get_by_code(code):
            raise ValidationError(f'Une UE avec le code "{code}" existe deja.')
        self._validate_specialite_ids(specialite_ids)
        return self.repo.create(
            code=code,
            name=name,
            specialite_ids=specialite_ids,
        )

    def update_ue(self, ue_id: str, **fields) -> UE:
        ue = self.get_ue(ue_id)
        if "code" in fields:
            fields["code"] = fields["code"].strip().upper()
            existing = self.repo.get_by_code(fields["code"])
            if existing and str(existing.pk) != str(ue_id):
                raise ValidationError(f'Le code "{fields["code"]}" est deja utilise.')
        if "specialite_ids" in fields:
            self._validate_specialite_ids(fields["specialite_ids"])
        return self.repo.update(ue, **fields)

    def delete_ue(self, ue_id: str) -> None:
        ue = self.get_ue(ue_id)
        self.repo.delete(ue)


# =============================================================================
# ECUE
# =============================================================================


class ECUEService:

    def __init__(
        self,
        repo: ECUERepository | None = None,
        ue_repo: UERepository | None = None,
    ):
        self.repo = repo or ECUERepository()
        self.ue_repo = ue_repo or UERepository()

    def list_ecues(self, ue_id: str | None = None):
        if ue_id:
            return self.repo.get_by_ue(ue_id)
        return self.repo.get_all()

    def get_ecue(self, ecue_id: str) -> ECUE:
        ecue = self.repo.get_by_id(ecue_id)
        if not ecue:
            raise ValidationError(f"ECUE introuvable : {ecue_id}.")
        return ecue

    def create_ecue(self, ue_id: str, code: str, name: str, coef: str | Decimal) -> ECUE:
        ue = self.ue_repo.get_by_id(ue_id)
        if not ue:
            raise ValidationError(f"UE introuvable : {ue_id}.")
        code = code.strip().upper()
        name = name.strip()
        if not code or not name:
            raise ValidationError("Le code et l'intitule de l'ECUE sont obligatoires.")
        try:
            coef = Decimal(str(coef))
            if coef < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            raise ValidationError("Le coefficient doit etre un nombre decimal >= 0.")
        if self.repo.get_by_code_and_ue(code, ue_id):
            raise ValidationError(f'L\'ECUE "{code}" existe deja dans cette UE.')
        return self.repo.create(ue_id=ue_id, code=code, name=name, coef=coef)

    def update_ecue(self, ecue_id: str, **fields) -> ECUE:
        ecue = self.get_ecue(ecue_id)
        if "code" in fields:
            fields["code"] = fields["code"].strip().upper()
            existing = self.repo.get_by_code_and_ue(fields["code"], str(ecue.ue_id))
            if existing and str(existing.pk) != str(ecue_id):
                raise ValidationError(f'L\'ECUE "{fields["code"]}" existe deja dans cette UE.')
        if "coef" in fields:
            try:
                fields["coef"] = Decimal(str(fields["coef"]))
                if fields["coef"] < 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise ValidationError("Le coefficient doit etre un nombre decimal >= 0.")
        return self.repo.update(ecue, **fields)

    def delete_ecue(self, ecue_id: str) -> None:
        ecue = self.get_ecue(ecue_id)
        self.repo.delete(ecue)
