"""
apps/niveau/services.py
"""
from django.core.exceptions import ValidationError

from apps.filiere.repositories import FiliereRepository
from apps.niveau.models import Niveau
from apps.niveau.repositories import NiveauRepository


class NiveauService:

    def __init__(
        self,
        repo: NiveauRepository | None = None,
        filiere_repo: FiliereRepository | None = None,
    ):
        self.repo = repo or NiveauRepository()
        self.filiere_repo = filiere_repo or FiliereRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

    def list_niveaux(self, filiere_id: str | None = None):
        if filiere_id:
            return self.repo.get_by_filiere(filiere_id)
        return self.repo.get_all()

    def get_niveau(self, niveau_id: str) -> Niveau:
        niveau = self.repo.get_by_id(niveau_id)
        if not niveau:
            raise ValidationError(f"Niveau introuvable : {niveau_id}.")
        return niveau

    # ── Commandes ─────────────────────────────────────────────────────────────

    def create_niveau(self, filiere_id: str, name: str) -> Niveau:
        if not self.filiere_repo.get_by_id(filiere_id):
            raise ValidationError(f"Filière introuvable : {filiere_id}.")
        # Validation choix
        valid_choices = [c[0] for c in Niveau.NiveauChoices.choices]
        if name not in valid_choices:
            raise ValidationError(
                f"Valeur invalide pour le niveau : « {name} ». "
                f"Valeurs autorisées : {', '.join(valid_choices)}."
            )
        if self.repo.get_by_filiere_and_name(filiere_id, name):
            raise ValidationError(
                f"Le niveau « {name} » existe déjà pour cette filière."
            )
        return self.repo.create(filiere_id=filiere_id, name=name)

    def delete_niveau(self, niveau_id: str) -> None:
        niveau = self.get_niveau(niveau_id)
        self.repo.delete(niveau)