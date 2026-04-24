"""
=============================================================================
 apps/users/serializers/creation_serializers.py
 Serializers pour la creation d'un etudiant et d'un bibliothecaire
=============================================================================
"""

import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.specialites.rules import (
    LIBELLE_NIVEAUX_AVEC_SPECIALITE,
)


def _validate_validity_window(data, *, require_both=False):
    date_debut = data.get('date_debut_validite')
    date_fin = data.get('date_fin_validite')

    if require_both and bool(date_debut) != bool(date_fin):
        raise serializers.ValidationError({
            'date_debut_validite': (
                "Les dates de debut et de fin doivent etre renseignees ensemble."
            ),
            'date_fin_validite': (
                "Les dates de debut et de fin doivent etre renseignees ensemble."
            ),
        })

    if date_debut and date_fin and date_fin < date_debut:
        raise serializers.ValidationError({
            'date_fin_validite': (
                "La date de fin doit etre posterieure ou egale a la date de debut."
            )
        })



# =============================================================================
# CREATION ETUDIANT (par Bibliothecaire ou Admin)
# =============================================================================

class EtudiantCreateSerializer(serializers.Serializer):
    """
    Donnees attendues pour creer un compte etudiant complet.

    Le bibliothecaire ou l'admin renseigne :
      - Les informations personnelles (nom, email, telephone)
      - La scolarite (filiere, niveau, specialite si le niveau l'exige)
      - Un mot de passe temporaire (l'etudiant devra le changer)

    Le matricule est genere automatiquement.
    Le compte est cree inactif par defaut (activation manuelle requise).
    """

    first_name = serializers.CharField(
        max_length=100,
        help_text="Prenom de l'etudiant. Ex: Ines"
    )
    last_name = serializers.CharField(
        max_length=100,
        help_text="Nom de famille de l'etudiant. Ex: IRIE"
    )
    email = serializers.EmailField(
        help_text="Email personnel de l'etudiant. Ex: etu.irie.m2c@etud-ci.edu"
    )
    phone = serializers.CharField(
        max_length=17,
        help_text="Numero de telephone avec indicatif. Ex: +2250701002003"
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de naissance. Format: YYYY-MM-DD. Ex: 2001-03-15"
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text=(
            "Mot de passe temporaire (min. 8 caracteres). "
            "L'etudiant devra le changer a sa premiere connexion."
        )
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe temporaire."
    )

    filiere_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            "UUID de la filiere. "
            f"Pour {LIBELLE_NIVEAUX_AVEC_SPECIALITE} -> filiere liee a la specialite."
        )
    )
    niveau_id = serializers.UUIDField(
        help_text="UUID du niveau. Ex: L1, L2, L3, M1, M2, DOCTORAT"
    )
    specialite_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            "UUID de la specialite. "
            f"OBLIGATOIRE pour {LIBELLE_NIVEAUX_AVEC_SPECIALITE}."
        )
    )
    annee_inscription = serializers.IntegerField(
        required=False,
        help_text="Annee d'inscription. Defaut: annee en cours. Ex: 2025"
    )
    date_debut_validite = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de debut de validite du compte. Format: YYYY-MM-DD."
    )
    date_fin_validite = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de fin de validite du compte. Format: YYYY-MM-DD."
    )

    activer_immediatement = serializers.BooleanField(
        default=False,
        help_text=(
            "Si True, le compte est active immediatement "
            "et la validite du compte est calculee depuis la periode configuree "
            "ou, a defaut, depuis la duree standard. "
            "Si False (defaut), le compte est cree inactif."
        )
    )

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError(
                "Numero invalide. Format attendu: +2250701002003"
            )
        return phone

    def validate_first_name(self, value):
        return value.strip().capitalize()

    def validate_last_name(self, value):
        return value.strip().upper()

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        _validate_validity_window(data, require_both=True)
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return data


class EtudiantUpdateSerializer(serializers.Serializer):
    """
    Mise a jour du profil etudiant (PATCH).
    Seuls les champs envoyes seront modifies.
    """

    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=17, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    filiere_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Nouvelle filiere (changement de parcours)."
    )
    niveau_id = serializers.UUIDField(
        required=False,
        help_text="Nouveau niveau (passage en annee superieure)."
    )
    specialite_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            f"Nouvelle specialite (obligatoire pour {LIBELLE_NIVEAUX_AVEC_SPECIALITE})."
        )
    )
    date_debut_validite = serializers.DateField(required=False, allow_null=True)
    date_fin_validite = serializers.DateField(required=False, allow_null=True)

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numero invalide.")
        return phone

    def validate(self, data):
        _validate_validity_window(data)
        return data


class EtudiantActiverSerializer(serializers.Serializer):
    """
    Activation / Reactivation du compte etudiant.
    Donnees attendues :
      {
        "action": "activer"   ou   "reactiver"
      }
    """

    action = serializers.ChoiceField(
        choices=['activer', 'reactiver'],
        help_text=(
            "'activer'   -> premiere activation en tenant compte des dates de "
            "validite si elles existent. "
            "'reactiver' -> relance le compte en reutilisant la fenetre de "
            "validite configuree ou la duree standard."
        )
    )


# =============================================================================
# CREATION PERSONNE EXTERNE
# =============================================================================

class PersonneExterneCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        max_length=100,
        help_text="Prenom de la personne externe."
    )
    last_name = serializers.CharField(
        max_length=100,
        help_text="Nom de la personne externe."
    )
    email = serializers.EmailField(
        help_text="Email de la personne externe."
    )
    phone = serializers.CharField(
        max_length=17,
        help_text="Numero de telephone avec indicatif. Ex: +2250701002003"
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de naissance. Format: YYYY-MM-DD."
    )
    numero_piece = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Numero de la piece d'identite."
    )
    profession = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="Profession de la personne externe."
    )
    lieu_habitation = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Lieu d'habitation."
    )
    date_debut_validite = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de debut de validite du compte. Format: YYYY-MM-DD."
    )
    date_fin_validite = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de fin de validite du compte. Format: YYYY-MM-DD."
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Mot de passe initial."
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe."
    )

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError(
                "Numero invalide. Format attendu: +2250701002003"
            )
        return phone

    def validate_first_name(self, value):
        return value.strip().capitalize()

    def validate_last_name(self, value):
        return value.strip().upper()

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        _validate_validity_window(data, require_both=True)
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data


class PersonneExterneUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=17, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    numero_piece = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    profession = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    lieu_habitation = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    date_debut_validite = serializers.DateField(required=False, allow_null=True)
    date_fin_validite = serializers.DateField(required=False, allow_null=True)

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numero invalide.")
        return phone

    def validate(self, data):
        _validate_validity_window(data)
        return data


# =============================================================================
# CREATION BIBLIOTHECAIRE (par Admin uniquement)
# =============================================================================

class BibliothecaireCreateSerializer(serializers.Serializer):
    """
    Donnees attendues pour creer un compte bibliothecaire.

    Seul l'administrateur peut creer un bibliothecaire.
    Le compte est cree avec le 2FA non configure -
    le bibliothecaire devra scanner son QR code a la premiere connexion.
    """

    first_name = serializers.CharField(
        max_length=100,
        help_text="Prenom du bibliothecaire. Ex: Mariam"
    )
    last_name = serializers.CharField(
        max_length=100,
        help_text="Nom du bibliothecaire. Ex: KONE"
    )
    email = serializers.EmailField(
        help_text=(
            "Email professionnel (sera utilise pour la connexion). "
            "Ex: biblio.kone@universite-ci.edu"
        )
    )
    phone = serializers.CharField(
        max_length=17,
        help_text="Numero de telephone. Ex: +2250701000002"
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de naissance. Ex: 1990-05-20"
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Mot de passe initial (min. 8 caracteres, 1 maj, 1 chiffre, 1 special)."
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe."
    )

    badge_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=(
            "Numero de badge unique. "
            "Si vide, aucun badge n'est assigne. "
            "Ex: BIB-2025-003"
        )
    )
    date_prise_poste = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de prise de poste. Ex: 2025-01-06"
    )

    peut_gerer_documents = serializers.BooleanField(
        default=True,
        help_text=(
            "Autorise la gestion des documents "
            "(ajout, modification, suppression). Defaut: True."
        )
    )
    peut_gerer_utilisateurs = serializers.BooleanField(
        default=False,
        help_text=(
            "Autorise la gestion des utilisateurs "
            "(creer/activer des etudiants). Defaut: False."
        )
    )

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError(
                "Numero invalide. Format attendu: +2250701000002"
            )
        return phone

    def validate_first_name(self, value):
        return value.strip().capitalize()

    def validate_last_name(self, value):
        return value.strip().upper()

    def validate_badge_number(self, value):
        if value:
            return value.strip().upper()
        return value

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data


class BibliothecaireUpdateSerializer(serializers.Serializer):
    """Mise a jour du profil bibliothecaire (PATCH)."""

    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=17, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    badge_number = serializers.CharField(max_length=20, required=False, allow_null=True)
    date_prise_poste = serializers.DateField(required=False, allow_null=True)
    peut_gerer_documents = serializers.BooleanField(required=False)
    peut_gerer_utilisateurs = serializers.BooleanField(required=False)

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numero invalide.")
        return phone


# =============================================================================
# SERIALIZERS DE REPONSE (lecture)
# =============================================================================

class EtudiantDetailSerializer(serializers.Serializer):
    """Reponse complete apres creation/lecture d'un etudiant."""

    id = serializers.UUIDField(
        help_text="UUID du profil etudiant. A utiliser dans /api/etudiants/{etudiant_id}/."
    )
    user_id = serializers.UUIDField(
        source='user.id',
        help_text="UUID du compte utilisateur lie."
    )
    matricule = serializers.CharField()
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone = serializers.CharField(source='user.phone')
    is_active = serializers.BooleanField(source='user.is_active')
    is_2fa_enabled = serializers.BooleanField(source='user.is_2fa_enabled')
    filiere = serializers.SerializerMethodField()
    niveau = serializers.SerializerMethodField()
    specialite = serializers.SerializerMethodField()
    annee_inscription = serializers.IntegerField()
    statut_compte = serializers.CharField()
    jours_restants = serializers.IntegerField(allow_null=True)
    pourcentage_validite = serializers.IntegerField(allow_null=True)
    date_debut_validite = serializers.DateField(allow_null=True)
    date_fin_validite = serializers.DateField(allow_null=True)
    compte_active_le = serializers.DateTimeField(allow_null=True)
    compte_expire_le = serializers.DateTimeField(allow_null=True)
    nb_reactivations = serializers.IntegerField()
    created_at = serializers.DateTimeField()

    def get_filiere(self, obj):
        if obj.filiere:
            return {'id': str(obj.filiere.pk), 'name': obj.filiere.name}
        return None

    def get_niveau(self, obj):
        if obj.niveau:
            return {'id': str(obj.niveau.pk), 'name': obj.niveau.name}
        return None

    def get_specialite(self, obj):
        if obj.specialite:
            return {'id': str(obj.specialite.pk), 'name': obj.specialite.name}
        return None


class PersonneExterneDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField(
        help_text=(
            "UUID du profil personne externe. "
            "A utiliser dans /api/personnes-externes/{personne_id}/."
        )
    )
    user_id = serializers.UUIDField(
        source='user.id',
        help_text="UUID du compte utilisateur lie."
    )
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone = serializers.CharField(source='user.phone')
    is_active = serializers.BooleanField(source='user.is_active')
    is_2fa_enabled = serializers.BooleanField(source='user.is_2fa_enabled')
    numero_piece = serializers.CharField()
    profession = serializers.CharField()
    lieu_habitation = serializers.CharField()
    statut_compte = serializers.CharField()
    jours_restants = serializers.IntegerField(allow_null=True)
    date_debut_validite = serializers.DateField(allow_null=True)
    date_fin_validite = serializers.DateField(allow_null=True)
    compte_active_le = serializers.DateTimeField(allow_null=True)
    compte_expire_le = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class BibliothecaireDetailSerializer(serializers.Serializer):
    """Reponse complete apres creation/lecture d'un bibliothecaire."""

    id = serializers.UUIDField(
        help_text="UUID du profil bibliothecaire. A utiliser dans /api/bibliothecaires/{biblio_id}/."
    )
    user_id = serializers.UUIDField(
        source='user.id',
        help_text="UUID du compte utilisateur lie."
    )
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone = serializers.CharField(source='user.phone')
    is_active = serializers.BooleanField(source='user.is_active')
    is_2fa_enabled = serializers.BooleanField(source='user.is_2fa_enabled')
    badge_number = serializers.CharField(allow_null=True)
    date_prise_poste = serializers.DateField(allow_null=True)
    peut_gerer_documents = serializers.BooleanField()
    peut_gerer_utilisateurs = serializers.BooleanField()
    created_at = serializers.DateTimeField()
