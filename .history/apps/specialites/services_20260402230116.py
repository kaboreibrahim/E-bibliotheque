"""
apps/specialites/services.py
"""
from django.core.exceptions import ValidationError

from apps.niveau.repositories import NiveauRepository
from apps.specialites.models import Specialite
from apps.specialites.repositories import SpecialiteRepository
from apps.specialites.rules import niveau_est_tronc_commun, LIBELLE_NIVEAUX_AVEC_SPECIALITE


class SpecialiteService:

    def __init__(
        self,
        repo: SpecialiteRepository | None = None,
        niveau_repo: NiveauRepository | None = None,
    ):
        self.repo = repo or SpecialiteRepository()
        self.niveau_repo = niveau_repo or NiveauRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

    def list_specialites(self, niveau_id: str | None = None, q: str | None = None):
        if q:
            return self.repo.search(q)
        if niveau_id:
            return self.repo.get_by_niveau(niveau_id)
        return self.repo.get_all()

    def get_specialite(self, specialite_id: str) -> Specialite:
        sp = self.repo.get_by_id(specialite_id)
        if not sp:
            raise ValidationError(f"Spécialité introuvable : {specialite_id}.")
        return sp

    # ── Commandes ─────────────────────────────────────────────────────────────

    def create_specialite(self, name: str, niveau_id: str) -> Specialite:
        name = name.strip()
        if not name:
            raise ValidationError("Le nom de la spécialité est obligatoire.")

        niveau = self.niveau_repo.get_by_id(niveau_id)
        if not niveau:
            raise ValidationError(f"Niveau introuvable : {niveau_id}.")

        if niveau_est_tronc_commun(niveau.name):
            raise ValidationError(
                f"Le niveau « {niveau.name} » n'accepte pas de spécialité. "
                f"Niveaux autorisés : {LIBELLE_NIVEAUX_AVEC_SPECIALITE}."
            )

        if self.repo.get_by_name_and_niveau(name, niveau_id):
            raise ValidationError(
                f"La spécialité « {name} » existe déjà pour ce niveau."
            )
        return self.repo.create(name=name, niveau_id=niveau_id)

    def update_specialite(self, specialite_id: str, name: str) -> Specialite:
        specialite = self.get_specialite(specialite_id)
        name = name.strip()
        if not name:
            raise ValidationError("Le nom ne peut pas être vide.")
        existing = self.repo.get_by_name_and_niveau(name, str(specialite.niveau_id))
        if existing and str(existing.pk) != str(specialite_id):
            raise ValidationError(
                f"La spécialité « {name} » existe déjà pour ce niveau."
            )
        return self.repo.update(specialite, name=name)

    def delete_specialite(self, specialite_id: str) -> None:
        specialite = self.get_specialite(specialite_id)
        self.repo.delete(specialite)