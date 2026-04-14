"""
=============================================================================
 apps/users/services/creation_service.py
 COUCHE SERVICE — Logique métier création Étudiant et Bibliothécaire
=============================================================================
"""

import logging
from dataclasses import dataclass, field

from apps.specialites.rules import niveau_accepte_specialite, niveau_est_tronc_commun
from apps.users.models.user_models import User
from apps.users.repositories.user_repository import UserRepository
from apps.users.repositories.etudiant_repository import (
    EtudiantRepository,
    BibliothecaireRepository,
)
from apps.users.repositories.personne_repository import PersonneExterneRepository
from apps.history.models import HistoriqueActionService as HAS

logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    success:     bool
    message:     str
    data:        dict = field(default_factory=dict)
    errors:      dict = field(default_factory=dict)
    http_status: int  = 200


# =============================================================================
# 🎓  SERVICE CRÉATION ÉTUDIANT
# =============================================================================

class EtudiantCreationService:
    """
    Logique métier pour la création d'un compte étudiant.

    Peut être appelé par :
      - Un Bibliothécaire (avec peut_gerer_utilisateurs=True)
      - Un Administrateur

    Flux :
      1. Vérifie unicité email + téléphone
      2. Vérifie cohérence niveau ↔ spécialité
      3. Crée le compte User (type ETUDIANT)
      4. Crée le profil Etudiant
      5. Active le compte si demandé
      6. Configure TOTP (génère le secret pour Google Authenticator)
      7. Log dans MongoDB
    """

    @staticmethod
    def creer_etudiant(
        data: dict,
        effectue_par: User,
    ) -> ServiceResult:
        """
        Crée un étudiant complet (User + profil Etudiant).

        Paramètres (issus du serializer validé) :
          first_name, last_name, email, phone, date_of_birth
          password
          filiere_id, niveau_id, specialite_id (obligatoire pour tous les niveaux)
          annee_inscription (optionnel)
          activer_immediatement (bool)
        """
        import pyotp
        from apps.filiere.models import Filiere
        from apps.niveau.models import Niveau
        from apps.specialites.models import Specialite

        # ── Vérifications unicité ────────────────────────────────────────────
        if UserRepository.exists_by_email(data['email']):
            return ServiceResult(
                success=False,
                message="Un compte avec cet email existe déjà.",
                errors={'email': ['Email déjà utilisé par un autre compte.']},
                http_status=400
            )

        if UserRepository.exists_by_phone(data['phone']):
            return ServiceResult(
                success=False,
                message="Un compte avec ce numéro de téléphone existe déjà.",
                errors={'phone': ['Téléphone déjà utilisé par un autre compte.']},
                http_status=400
            )

        # ── Résoudre les FK ───────────────────────────────────────────────────
        niveau = None
        if data.get('niveau_id'):
            try:
                niveau = Niveau.objects.get(pk=data['niveau_id'])
            except Niveau.DoesNotExist:
                return ServiceResult(
                    success=False,
                    message="Niveau introuvable.",
                    errors={'niveau_id': ['Niveau inexistant.']},
                    http_status=400
                )

        filiere = None
        if data.get('filiere_id'):
            try:
                filiere = Filiere.objects.get(pk=data['filiere_id'])
            except Filiere.DoesNotExist:
                return ServiceResult(
                    success=False,
                    message="Filière introuvable.",
                    errors={'filiere_id': ['Filière inexistante.']},
                    http_status=400
                )

        specialite = None
        if data.get('specialite_id'):
            try:
                specialite = Specialite.objects.get(pk=data['specialite_id'])
            except Specialite.DoesNotExist:
                return ServiceResult(
                    success=False,
                    message="Spécialité introuvable.",
                    errors={'specialite_id': ['Spécialité inexistante.']},
                    http_status=400
                )

        # ── Règle métier : spécialité ↔ niveau ───────────────────────────────
        if niveau:

            if niveau_est_tronc_commun(niveau.name) and specialite:
                return ServiceResult(
                    success=False,
                    message=f"Les étudiants en {niveau.name} ne doivent pas avoir de spécialité.",
                    errors={'specialite_id': ['Spécialité non autorisée pour ce niveau.']},
                    http_status=400
                )

            if niveau_accepte_specialite(niveau.name) and not specialite:
                return ServiceResult(
                    success=False,
                    message=f"Une spécialité est obligatoire pour le niveau {niveau.name}.",
                    errors={'specialite_id': ['Spécialité requise pour ce niveau.']},
                    http_status=400
                )

            if specialite and niveau_accepte_specialite(niveau.name):
                if str(specialite.niveau_id) != str(niveau.pk):
                    return ServiceResult(
                        success=False,
                        message="La spécialité choisie n'appartient pas à ce niveau.",
                        errors={'specialite_id': ['Incohérence niveau ↔ spécialité.']},
                        http_status=400
                    )

        # ── Créer le compte User ──────────────────────────────────────────────
        user = UserRepository.create(
            email       = data['email'],
            password    = data['password'],
            first_name  = data['first_name'],
            last_name   = data['last_name'],
            phone       = data['phone'],
            user_type   = 'ETUDIANT',
            date_of_birth = data.get('date_of_birth'),
            is_active   = False,    # inactif par défaut
        )

        # ── Configurer TOTP (Google Authenticator) ────────────────────────────
        # On génère le secret maintenant — l'étudiant le configurera lors
        # de sa première connexion via l'endpoint /auth/totp/setup/
        totp_secret = pyotp.random_base32()
        import pyotp as _pyotp
        UserRepository.update(user, totp_secret=totp_secret)

        qr_uri = _pyotp.TOTP(totp_secret).provisioning_uri(
            name=user.email,
            issuer_name="Bibliothèque Universitaire CI"
        )

        # ── Créer le profil Etudiant ──────────────────────────────────────────
        etudiant = EtudiantRepository.create(
            user              = user,
            filiere           = filiere,
            niveau            = niveau,
            specialite        = specialite,
            annee_inscription = data.get('annee_inscription'),
        )

        # ── Activer si demandé ────────────────────────────────────────────────
        if data.get('activer_immediatement', False):
            EtudiantRepository.activer(etudiant, effectue_par=effectue_par)

        # ── Log MongoDB ───────────────────────────────────────────────────────
        HAS.log_utilisateur(
            'CREATION',
            auteur      = effectue_par,
            cible_user  = user,
            details     = {
                'matricule':   etudiant.matricule,
                'niveau':      niveau.name if niveau else None,
                'specialite':  str(specialite) if specialite else None,
                'active':      data.get('activer_immediatement', False),
            }
        )

        return ServiceResult(
            success=True,
            message=(
                f"Compte étudiant créé avec succès. "
                f"Matricule : {etudiant.matricule}. "
                + ("Compte activé." if data.get('activer_immediatement') else
                   "Compte inactif — activation manuelle requise.")
            ),
            data={
                'etudiant_id':   str(etudiant.id),
                'user_id':       str(user.id),
                'matricule':     etudiant.matricule,
                'email':         user.email,
                'nom_complet':   user.get_full_name(),
                'statut_compte': etudiant.statut_compte,
                'jours_restants':etudiant.jours_restants,
                'compte_expire_le': (
                    etudiant.compte_expire_le.isoformat()
                    if etudiant.compte_expire_le else None
                ),
                # QR code à afficher à l'écran pour que l'étudiant configure
                # Google Authenticator lors de sa première visite
                'totp_setup': {
                    'totp_secret': totp_secret,
                    'qr_uri':      qr_uri,
                    'instructions': (
                        "Transmettez ces informations à l'étudiant pour qu'il "
                        "configure Google Authenticator sur son téléphone."
                    )
                }
            },
            http_status=201
        )

    @staticmethod
    def activer_compte(etudiant_id: str, effectue_par: User, action: str) -> ServiceResult:
        """
        Active ou réactive le compte d'un étudiant.
        action: 'activer' | 'reactiver'
        """
        etudiant = EtudiantRepository.get_by_id(etudiant_id)
        if not etudiant:
            return ServiceResult(
                success=False,
                message="Étudiant introuvable.",
                http_status=404
            )

        if action == 'activer':
            if etudiant.compte_active_le:
                return ServiceResult(
                    success=False,
                    message="Ce compte a déjà été activé. Utilisez 'reactiver' pour renouveler.",
                    errors={'action': ['Utilisez reactiver.']},
                    http_status=400
                )
            EtudiantRepository.activer(etudiant, effectue_par=effectue_par)
            msg = (
                f"Compte de {etudiant.user.get_full_name()} activé. "
                f"Expire le {etudiant.compte_expire_le.strftime('%d/%m/%Y')}."
            )
        else:  # reactiver
            EtudiantRepository.reactiver(etudiant, effectue_par=effectue_par)
            msg = (
                f"Compte de {etudiant.user.get_full_name()} réactivé "
                f"({etudiant.nb_reactivations}e réactivation). "
                f"Expire le {etudiant.compte_expire_le.strftime('%d/%m/%Y')}."
            )

        HAS.log_utilisateur(
            action.upper(),
            auteur     = effectue_par,
            cible_user = etudiant.user,
            details    = {
                'action':          action,
                'expire_le':       etudiant.compte_expire_le.isoformat(),
                'nb_reactivations': etudiant.nb_reactivations,
            }
        )

        return ServiceResult(
            success=True,
            message=msg,
            data={
                'matricule':       etudiant.matricule,
                'statut_compte':   etudiant.statut_compte,
                'jours_restants':  etudiant.jours_restants,
                'compte_active_le':etudiant.compte_active_le.isoformat(),
                'compte_expire_le':etudiant.compte_expire_le.isoformat(),
                'nb_reactivations':etudiant.nb_reactivations,
            },
            http_status=200
        )


# =============================================================================
# 📖  SERVICE CRÉATION BIBLIOTHÉCAIRE
# =============================================================================

class BibliothecaireCreationService:
    """
    Logique métier pour la création d'un compte bibliothécaire.

    Réservé à l'administrateur uniquement.

    Flux :
      1. Vérifie unicité email + téléphone + badge
      2. Crée le compte User (type BIBLIOTHECAIRE, is_staff=True)
      3. Crée le profil Bibliothecaire avec les permissions
      4. Génère le secret TOTP (Google Authenticator à configurer)
      5. Log dans MongoDB
    """

    @staticmethod
    def creer_bibliothecaire(data: dict, effectue_par: User) -> ServiceResult:
        """
        Crée un bibliothécaire complet (User + profil Bibliothecaire).
        """
        import pyotp

        # ── Vérifications unicité ────────────────────────────────────────────
        if UserRepository.exists_by_email(data['email']):
            return ServiceResult(
                success=False,
                message="Un compte avec cet email existe déjà.",
                errors={'email': ['Email déjà utilisé.']},
                http_status=400
            )

        if UserRepository.exists_by_phone(data['phone']):
            return ServiceResult(
                success=False,
                message="Un compte avec ce numéro de téléphone existe déjà.",
                errors={'phone': ['Téléphone déjà utilisé.']},
                http_status=400
            )

        if data.get('badge_number') and BibliothecaireRepository.badge_exists(data['badge_number']):
            return ServiceResult(
                success=False,
                message=f"Le badge '{data['badge_number']}' est déjà assigné à un autre bibliothécaire.",
                errors={'badge_number': ['Numéro de badge déjà utilisé.']},
                http_status=400
            )

        # ── Créer le compte User ──────────────────────────────────────────────
        user = UserRepository.create(
            email        = data['email'],
            password     = data['password'],
            first_name   = data['first_name'],
            last_name    = data['last_name'],
            phone        = data['phone'],
            user_type    = 'BIBLIOTHECAIRE',
            date_of_birth= data.get('date_of_birth'),
            is_active    = True,    # actif immédiatement
            is_staff     = True,    # accès admin Django
        )

        # ── Générer le secret TOTP ─────────────────────────────────────────────
        # Le bibliothécaire devra scanner le QR code à sa première connexion
        totp_secret = pyotp.random_base32()
        qr_uri = pyotp.TOTP(totp_secret).provisioning_uri(
            name=user.email,
            issuer_name="Bibliothèque Universitaire CI"
        )
        UserRepository.update(user, totp_secret=totp_secret)
        # Note: is_2fa_enabled reste False jusqu'à la confirmation via /totp/confirm/

        # ── Créer le profil Bibliothecaire ────────────────────────────────────
        biblio = BibliothecaireRepository.create(
            user                    = user,
            badge_number            = data.get('badge_number'),
            date_prise_poste        = data.get('date_prise_poste'),
            peut_gerer_documents    = data.get('peut_gerer_documents', True),
            peut_gerer_utilisateurs = data.get('peut_gerer_utilisateurs', False),
        )

        # ── Log MongoDB ───────────────────────────────────────────────────────
        HAS.log_utilisateur(
            'CREATION',
            auteur     = effectue_par,
            cible_user = user,
            details    = {
                'badge_number':             biblio.badge_number,
                'peut_gerer_documents':    biblio.peut_gerer_documents,
                'peut_gerer_utilisateurs': biblio.peut_gerer_utilisateurs,
            }
        )

        return ServiceResult(
            success=True,
            message=(
                f"Compte bibliothécaire créé avec succès pour {user.get_full_name()}. "
                f"Le bibliothécaire doit configurer Google Authenticator "
                f"à sa première connexion."
            ),
            data={
                'bibliothecaire_id': str(biblio.id),
                'user_id':           str(user.id),
                'email':             user.email,
                'nom_complet':       user.get_full_name(),
                'badge_number':      biblio.badge_number,
                'permissions': {
                    'peut_gerer_documents':    biblio.peut_gerer_documents,
                    'peut_gerer_utilisateurs': biblio.peut_gerer_utilisateurs,
                },
                # QR code à transmettre au bibliothécaire
                'totp_setup': {
                    'totp_secret': totp_secret,
                    'qr_uri':      qr_uri,
                    'instructions': (
                        "Transmettez ces informations au bibliothécaire. "
                        "Il devra scanner ce QR code avec Google Authenticator "
                        "et confirmer via POST /api/auth/totp/confirm/ "
                        "avant de pouvoir se connecter."
                    )
                }
            },
            http_status=201
        )


class PersonneExterneCreationService:
    """
    Logique metier pour la creation d'un compte personne externe.
    """

    @staticmethod
    def creer_personne_externe(data: dict, effectue_par: User) -> ServiceResult:
        if UserRepository.exists_by_email(data['email']):
            return ServiceResult(
                success=False,
                message="Un compte avec cet email existe deja.",
                errors={'email': ['Email deja utilise par un autre compte.']},
                http_status=400
            )

        if UserRepository.exists_by_phone(data['phone']):
            return ServiceResult(
                success=False,
                message="Un compte avec ce numero de telephone existe deja.",
                errors={'phone': ['Telephone deja utilise par un autre compte.']},
                http_status=400
            )

        user = UserRepository.create(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
            user_type='PERSONNE_EXTERNE',
            date_of_birth=data.get('date_of_birth'),
            is_active=True,
        )

        personne = PersonneExterneRepository.create(user=user)
        PersonneExterneRepository.update(
            personne,
            numero_piece=data.get('numero_piece', ''),
            profession=data.get('profession', ''),
            lieu_habitation=data.get('lieu_habitation', ''),
        )
        personne.refresh_from_db()

        HAS.log_utilisateur(
            'CREATION',
            auteur=effectue_par,
            cible_user=user,
            details={
                'profil_type': 'PERSONNE_EXTERNE',
                'numero_piece': personne.numero_piece,
                'profession': personne.profession,
                'lieu_habitation': personne.lieu_habitation,
            }
        )

        return ServiceResult(
            success=True,
            message=(
                f"Compte personne externe cree avec succes pour {user.get_full_name()}. "
                "Le compte est actif immediatement."
            ),
            data={
                'personne_externe_id': str(personne.id),
                'user_id': str(user.id),
                'email': user.email,
                'nom_complet': user.get_full_name(),
                'user_type': user.user_type,
                'numero_piece': personne.numero_piece,
                'profession': personne.profession,
                'lieu_habitation': personne.lieu_habitation,
            },
            http_status=201
        )
