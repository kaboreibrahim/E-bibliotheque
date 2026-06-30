"""
apps/filiere/services.py
Couche service – logique métier filière.
"""
from django.core.exceptions import ValidationError

from apps.filiere.models import Filiere
from apps.filiere.repositories import FiliereRepository


class FiliereService:

    def __init__(self, repo: FiliereRepository | None = None):
        self.repo = repo or FiliereRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

    def list_filieres(self):
        return self.repo.get_all()

    def get_filiere(self, filiere_id: str) -> Filiere:
        filiere = self.repo.get_by_id(filiere_id)
        if not filiere:
            raise ValidationError(f"Filière introuvable : {filiere_id}.")
        return filiere

    def search_filieres(self, q: str):
        return self.repo.search(q)

    # ── Commandes ─────────────────────────────────────────────────────────────

    def create_filiere(self, name: str) -> Filiere:
        name = name.strip()
        if not name:
            raise ValidationError("Le nom de la filière est obligatoire.")
        if self.repo.get_by_name(name):
            raise ValidationError(f"Une filière nommée « {name} » existe déjà.")
        return self.repo.create(name=name)

    def update_filiere(self, filiere_id: str, name: str) -> Filiere:
        filiere = self.get_filiere(filiere_id)
        name = name.strip()
        if not name:
            raise ValidationError("Le nom ne peut pas être vide.")
        existing = self.repo.get_by_name(name)
        if existing and str(existing.pk) != str(filiere_id):
            raise ValidationError(f"Une filière nommée « {name} » existe déjà.")
        return self.repo.update(filiere, name=name)

    def delete_filiere(self, filiere_id: str) -> None:
        filiere = self.get_filiere(filiere_id)
        self.repo.delete(filiere)