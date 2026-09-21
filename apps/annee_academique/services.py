"""
apps/annee_academique/services.py
Couche service — logique metier annee academique.
"""
from django.core.exceptions import ValidationError

from apps.annee_academique.models import AnneeAcademique
from apps.annee_academique.repositories import AnneeAcademiqueRepository


class AnneeAcademiqueService:

    def __init__(self, repo: AnneeAcademiqueRepository | None = None):
        self.repo = repo or AnneeAcademiqueRepository()

    # ── Requêtes ──────────────────────────────────────────────────────────────

    def list_annees(self):
        return self.repo.get_all()

    def get_annee(self, annee_id: str) -> AnneeAcademique:
        annee = self.repo.get_by_id(annee_id)
        if not annee:
            raise ValidationError(f"Année académique introuvable : {annee_id}.")
        return annee

    def get_annee_courante(self) -> AnneeAcademique | None:
        return self.repo.get_courante()

    # ── Commandes ─────────────────────────────────────────────────────────────

    def create_annee(self, *, date_debut, date_fin, est_courante=False) -> AnneeAcademique:
        return self.repo.create(
            date_debut=date_debut,
            date_fin=date_fin,
            est_courante=est_courante,
        )

    def update_annee(self, annee_id: str, **fields) -> AnneeAcademique:
        annee = self.get_annee(annee_id)
        return self.repo.update(annee, **fields)

    def delete_annee(self, annee_id: str) -> None:
        annee = self.get_annee(annee_id)
        self.repo.delete(annee)
