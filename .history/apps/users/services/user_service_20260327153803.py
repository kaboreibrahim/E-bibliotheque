"""
=============================================================================
 apps/users/services/user_service.py
 COUCHE SERVICE — Logique métier gestion utilisateurs (CRUD + profils)
=============================================================================
"""

import logging
from dataclasses import dataclass, field

from apps.users.models.user_models import User
from apps.users.repositories.user_repository import UserRepository
from logs.models import HistoriqueActionService as HAS

logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    success:     bool
    message:     str
    data:        dict = field(default_factory=dict)
    errors:      dict = field(default_factory=dict)
    http_status: int  = 200


class UserService:
    """Logique métier liée aux utilisateurs (création, mise à jour, désactivation)."""

    @staticmethod
    def create_user(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str,
        user_type: str,
        effectue_par: User = None,
        **extra_fields
    ) -> ServiceResult:
        """
        Crée un utilisateur avec validation métier.
        - Vérifie unicité email et téléphone
        - Crée le profil Etudiant ou Bibliothecaire si nécessaire
        - Log l'action dans MongoDB
        """
        if UserRepository.exists_by_email(email):
            return ServiceResult(
                success=False,
                message="Un compte avec cet email existe déjà.",
                errors={'email': ['Email déjà utilisé.']},
                http_status=400
            )

        if UserRepository.exists_by_phone(phone):
            return ServiceResult(
                success=False,
                message="Un compte avec ce numéro de téléphone existe déjà.",
                errors={'phone': ['Téléphone déjà utilisé.']},
                http_status=400
            )

        user = UserRepository.create(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=user_type,
            **extra_fields
        )

        # Log MongoDB
        if effectue_par:
            HAS.log_utilisateur('CREATION', auteur=effectue_par, cible_user=user)

        return ServiceResult(
            success=True,
            message=f"Compte créé avec succès pour {user.get_full_name()}.",
            data={'user_id': str(user.id), 'email': user.email},
            http_status=201
        )

    @staticmethod
    def update_user(
        user: User,
        fields: dict,
        effectue_par: User = None
    ) -> ServiceResult:
        """
        Met à jour les champs autorisés d'un utilisateur.
        Vérifie l'unicité email/téléphone si modifiés.
        """
        # Vérifier unicité email si changé
        new_email = fields.get('email')
        if new_email and new_email.lower() != user.email.lower():
            if UserRepository.exists_by_email(new_email):
                return ServiceResult(
                    success=False,
                    message="Cet email est déjà utilisé par un autre compte.",
                    errors={'email': ['Email déjà utilisé.']},
                    http_status=400
                )

        # Vérifier unicité téléphone si changé
        new_phone = fields.get('phone')
        if new_phone and new_phone != user.phone:
            if UserRepository.exists_by_phone(new_phone):
                return ServiceResult(
                    success=False,
                    message="Ce numéro est déjà utilisé par un autre compte.",
                    errors={'phone': ['Téléphone déjà utilisé.']},
                    http_status=400
                )

        updated_user = UserRepository.update(user, **fields)

        if effectue_par:
            HAS.log_utilisateur(
                'MODIF', auteur=effectue_par, cible_user=updated_user,
                details={'champs_modifies': list(fields.keys())}
            )

        return ServiceResult(
            success=True,
            message="Compte mis à jour avec succès.",
            data={'user_id': str(updated_user.id)},
            http_status=200
        )

    @staticmethod
    def deactivate_user(user: User, effectue_par: User = None) -> ServiceResult:
        """Désactive un compte utilisateur."""
        if not user.is_active:
            return ServiceResult(
                success=False,
                message="Ce compte est déjà désactivé.",
                http_status=400
            )
        UserRepository.deactivate(user)

        if effectue_par:
            HAS.log_utilisateur('DESACTIVE', auteur=effectue_par, cible_user=user)

        return ServiceResult(
            success=True,
            message=f"Compte de {user.get_full_name()} désactivé.",
            http_status=200
        )

    @staticmethod
    def delete_user(user: User, effectue_par: User = None) -> ServiceResult:
        """Suppression logique (soft delete)."""
        if effectue_par:
            HAS.log_utilisateur('SUPPRIME', auteur=effectue_par, cible_user=user)

        UserRepository.soft_delete(user)
        return ServiceResult(
            success=True,
            message="Compte supprimé.",
            http_status=204
        )

    @staticmethod
    def get_profile(user: User) -> ServiceResult:
        """Retourne le profil complet d'un utilisateur avec son profil lié."""
        data = {
            'id':            str(user.id),
            'email':         user.email,
            'first_name':    user.first_name,
            'last_name':     user.last_name,
            'phone':         user.phone,
            'user_type':     user.user_type,
            'is_active':     user.is_active,
            'is_2fa_enabled':user.is_2fa_enabled,
            'created_at':    user.created_at.isoformat(),
        }

        # Enrichir selon le type
        if user.user_type == 'ETUDIANT' and hasattr(user, 'profil_etudiant'):
            etu = user.profil_etudiant
            data['profil'] = {
                'matricule':       etu.matricule,
                'filiere':         str(etu.filiere) if etu.filiere else None,
                'niveau':          str(etu.niveau) if etu.niveau else None,
                'specialite':      str(etu.specialite) if etu.specialite else None,
                'statut_compte':   etu.statut_compte,
                'jours_restants':  etu.jours_restants,
                'pourcentage':     etu.pourcentage_validite,
            }
        elif user.user_type == 'BIBLIOTHECAIRE' and hasattr(user, 'profil_bibliothecaire'):
            bib = user.profil_bibliothecaire
            data['profil'] = {
                'badge_number':             bib.badge_number,
                'peut_gerer_documents':    bib.peut_gerer_documents,
                'peut_gerer_utilisateurs': bib.peut_gerer_utilisateurs,
                'date_prise_poste':        str(bib.date_prise_poste) if bib.date_prise_poste else None,
            }

        return ServiceResult(success=True, message="Profil récupéré.", data=data)