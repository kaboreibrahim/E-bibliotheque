"""
=============================================================================
 apps/users/repositories/etudiant_repository.py
 Accès ORM — Etudiant uniquement. Aucune logique métier ici.
=============================================================================
"""

from django.db.models import QuerySet
from apps.users.models import Etudiant
from apps.users.models import Bibliothecaire
from apps.users.models import User


class EtudiantRepository:

    # ── Lecture ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(etudiant_id: str) -> Etudiant | None:
        try:
            return Etudiant.objects.select_related(
                'user', 'filiere', 'niveau', 'specialite',
                'derniere_reactivation_par'
            ).get(id=etudiant_id)
        except Etudiant.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> Etudiant | None:
        try:
            return Etudiant.objects.select_related(
                'filiere', 'niveau', 'specialite'
            ).get(user=user)
        except Etudiant.DoesNotExist:
            return None

    @staticmethod
    def get_by_matricule(matricule: str) -> Etudiant | None:
        try:
            return Etudiant.objects.select_related('user').get(matricule=matricule)
        except Etudiant.DoesNotExist:
            return None

    @staticmethod
    def matricule_exists(matricule: str) -> bool:
        return Etudiant.objects.filter(matricule=matricule).exists()

    @staticmethod
    def get_all(filters: dict = None) -> QuerySet:
        qs = Etudiant.objects.select_related(
            'user', 'filiere', 'niveau', 'specialite'
        ).all()
        if filters:
            qs = qs.filter(**filters)
        return qs.order_by('user__last_name')

    @staticmethod
    def get_expires_soon(jours: int = 7) -> QuerySet:
        """Retourne les étudiants dont le compte expire dans moins de N jours."""
        from django.utils import timezone
        from datetime import timedelta
        limite = timezone.now() + timedelta(days=jours)
        return Etudiant.objects.filter(
            compte_expire_le__lte=limite,
            compte_expire_le__gt=timezone.now(),
            user__is_active=True
        ).select_related('user', 'filiere', 'niveau')

    @staticmethod
    def get_expired() -> QuerySet:
        """Retourne les étudiants dont le compte est expiré."""
        from django.utils import timezone
        return Etudiant.objects.filter(
            compte_expire_le__lt=timezone.now(),
            user__is_active=True
        ).select_related('user')

    # ── Écriture ──────────────────────────────────────────────────────────────

    @staticmethod
    def create(user: User, filiere, niveau, specialite=None,
               annee_inscription: int = None) -> Etudiant:
        from django.utils import timezone
        return Etudiant.objects.create(
            user=user,
            filiere=filiere,
            niveau=niveau,
            specialite=specialite,
            annee_inscription=annee_inscription or timezone.now().year,
        )

    @staticmethod
    def update(etudiant: Etudiant, **fields) -> Etudiant:
        for key, value in fields.items():
            setattr(etudiant, key, value)
        etudiant.save(update_fields=list(fields.keys()) + ['updated_at'])
        return etudiant

    @staticmethod
    def activer(etudiant: Etudiant, effectue_par: User = None) -> Etudiant:
        etudiant.activer_compte(effectue_par=effectue_par)
        return etudiant

    @staticmethod
    def reactiver(etudiant: Etudiant, effectue_par: User = None) -> Etudiant:
        etudiant.reactiver_compte(effectue_par=effectue_par)
        return etudiant

    @staticmethod
    def desactiver(etudiant: Etudiant) -> None:
        etudiant.desactiver_compte()

    @staticmethod
    def soft_delete(etudiant: Etudiant) -> None:
        etudiant.delete()


# =============================================================================
# 📖  BIBLIOTHÉCAIRE REPOSITORY
# =============================================================================

"""
=============================================================================
 apps/users/repositories/bibliothecaire_repository.py
=============================================================================
"""



class BibliothecaireRepository:

    @staticmethod
    def get_by_id(biblio_id: str) -> Bibliothecaire | None:
        try:
            return Bibliothecaire.objects.select_related('user').get(id=biblio_id)
        except Bibliothecaire.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> Bibliothecaire | None:
        try:
            return Bibliothecaire.objects.select_related('user').get(user=user)
        except Bibliothecaire.DoesNotExist:
            return None

    @staticmethod
    def badge_exists(badge_number: str) -> bool:
        return Bibliothecaire.objects.filter(badge_number=badge_number).exists()

    @staticmethod
    def get_all(filters: dict = None) -> QuerySet:
        qs = Bibliothecaire.objects.select_related('user').all()
        if filters:
            qs = qs.filter(**filters)
        return qs.order_by('user__last_name')

    @staticmethod
    def create(
        user: User,
        badge_number: str = None,
        date_prise_poste=None,
        peut_gerer_documents: bool = True,
        peut_gerer_utilisateurs: bool = False,
    ) -> Bibliothecaire:
        return Bibliothecaire.objects.create(
            user=user,
            badge_number=badge_number,
            date_prise_poste=date_prise_poste,
            peut_gerer_documents=peut_gerer_documents,
            peut_gerer_utilisateurs=peut_gerer_utilisateurs,
        )

    @staticmethod
    def update(biblio: Bibliothecaire, **fields) -> Bibliothecaire:
        for key, value in fields.items():
            setattr(biblio, key, value)
        biblio.save(update_fields=list(fields.keys()) + ['updated_at'])
        return biblio

    @staticmethod
    def soft_delete(biblio: Bibliothecaire) -> None:
        biblio.delete()