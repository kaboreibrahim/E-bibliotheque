"""
=============================================================================
 apps/users/serializers/creation_serializers.py
 Serializers pour la création d'un étudiant et d'un bibliothécaire
=============================================================================
"""

import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


# =============================================================================
# 🎓  CRÉATION ÉTUDIANT (par Bibliothécaire ou Admin)
# =============================================================================

class EtudiantCreateSerializer(serializers.Serializer):
    """
    Données attendues pour créer un compte étudiant complet.

    Le bibliothécaire ou l'admin renseigne :
      - Les informations personnelles (nom, email, téléphone)
      - La scolarité (filière, niveau, spécialité si M1/M2/DOCTORAT)
      - Un mot de passe temporaire (l'étudiant devra le changer)

    Le matricule est généré automatiquement.
    Le compte est créé inactif par défaut (activation manuelle requise).
    """

    # ── Informations personnelles ──────────────────────────────────────────────
    first_name = serializers.CharField(
        max_length=100,
        help_text="Prénom de l'étudiant. Ex: Inès"
    )
    last_name = serializers.CharField(
        max_length=100,
        help_text="Nom de famille de l'étudiant. Ex: IRIÉ"
    )
    email = serializers.EmailField(
        help_text="Email personnel de l'étudiant. Ex: etu.irie.m2c@etud-ci.edu"
    )
    phone = serializers.CharField(
        max_length=17,
        help_text="Numéro de téléphone avec indicatif. Ex: +2250701002003"
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de naissance. Format: YYYY-MM-DD. Ex: 2001-03-15"
    )

    # ── Mot de passe temporaire ────────────────────────────────────────────────
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text=(
            "Mot de passe temporaire (min. 8 caractères). "
            "L'étudiant devra le changer à sa première connexion."
        )
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe temporaire."
    )

    # ── Scolarité ──────────────────────────────────────────────────────────────
    filiere_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            "UUID de la filière. "
            "Pour L1/L2/L3 (tronc commun) → filière 'Droit Général'. "
            "Pour M1/M2 → filière de la spécialité."
        )
    )
    niveau_id = serializers.UUIDField(
        help_text="UUID du niveau. Ex: L1, L2, L3, M1, M2, DOCTORAT"
    )
    specialite_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            "UUID de la spécialité. "
            "OBLIGATOIRE pour M1, M2 et DOCTORAT. "
            "LAISSER VIDE pour L1, L2 et L3 (tronc commun)."
        )
    )
    annee_inscription = serializers.IntegerField(
        required=False,
        help_text="Année d'inscription. Défaut: année en cours. Ex: 2025"
    )

    # ── Options ────────────────────────────────────────────────────────────────
    activer_immediatement = serializers.BooleanField(
        default=False,
        help_text=(
            "Si True, le compte est activé immédiatement "
            "et le cycle de 30 jours démarre maintenant. "
            "Si False (défaut), le compte est créé inactif."
        )
    )

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError(
                "Numéro invalide. Format attendu: +2250701002003"
            )
        return phone

    def validate_first_name(self, value):
        return value.strip().capitalize()

    def validate_last_name(self, value):
        return value.strip().upper()

    def validate(self, data):
        # Mots de passe
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Les mots de passe ne correspondent pas."
            })
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return data


class EtudiantUpdateSerializer(serializers.Serializer):
    """
    Mise à jour du profil étudiant (PATCH).
    Seuls les champs envoyés seront modifiés.
    """
    first_name    = serializers.CharField(max_length=100, required=False)
    last_name     = serializers.CharField(max_length=100, required=False)
    phone         = serializers.CharField(max_length=17,  required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    filiere_id    = serializers.UUIDField(required=False, allow_null=True,
                        help_text="Nouvelle filière (changement de parcours).")
    niveau_id     = serializers.UUIDField(required=False,
                        help_text="Nouveau niveau (passage en année supérieure).")
    specialite_id = serializers.UUIDField(required=False, allow_null=True,
                        help_text="Nouvelle spécialité (obligatoire pour M1/M2/DOC).")

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numéro invalide.")
        return phone


class EtudiantActiverSerializer(serializers.Serializer):
    """
    Activation / Réactivation du compte étudiant.
    Données attendues :
      {
        "action": "activer"   ou   "reactiver"
      }
    """
    action = serializers.ChoiceField(
        choices=['activer', 'reactiver'],
        help_text=(
            "'activer'   → première activation (démarre le cycle de 30 jours). "
            "'reactiver' → renouvelle le cycle de 30 jours (compte expiré)."
        )
    )


# =============================================================================
# 📖  CRÉATION BIBLIOTHÉCAIRE (par Admin uniquement)
# =============================================================================

class BibliothecaireCreateSerializer(serializers.Serializer):
    """
    Données attendues pour créer un compte bibliothécaire.

    Seul l'administrateur peut créer un bibliothécaire.
    Le compte est créé avec le 2FA non configuré —
    le bibliothécaire devra scanner son QR code à la première connexion.
    """

    # ── Informations personnelles ──────────────────────────────────────────────
    first_name = serializers.CharField(
        max_length=100,
        help_text="Prénom du bibliothécaire. Ex: Mariam"
    )
    last_name = serializers.CharField(
        max_length=100,
        help_text="Nom du bibliothécaire. Ex: KONÉ"
    )
    email = serializers.EmailField(
        help_text=(
            "Email professionnel (sera utilisé pour la connexion). "
            "Ex: biblio.kone@universite-ci.edu"
        )
    )
    phone = serializers.CharField(
        max_length=17,
        help_text="Numéro de téléphone. Ex: +2250701000002"
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de naissance. Ex: 1990-05-20"
    )

    # ── Mot de passe ──────────────────────────────────────────────────────────
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Mot de passe initial (min. 8 caractères, 1 maj, 1 chiffre, 1 spécial)."
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe."
    )

    # ── Profil bibliothécaire ─────────────────────────────────────────────────
    badge_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=(
            "Numéro de badge unique. "
            "Si vide, aucun badge n'est assigné. "
            "Ex: BIB-2025-003"
        )
    )
    date_prise_poste = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date de prise de poste. Ex: 2025-01-06"
    )

    # ── Permissions ───────────────────────────────────────────────────────────
    peut_gerer_documents = serializers.BooleanField(
        default=True,
        help_text=(
            "Autorise la gestion des documents "
            "(ajout, modification, suppression). Défaut: True."
        )
    )
    peut_gerer_utilisateurs = serializers.BooleanField(
        default=False,
        help_text=(
            "Autorise la gestion des utilisateurs "
            "(créer/activer des étudiants). Défaut: False."
        )
    )

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError(
                "Numéro invalide. Format attendu: +2250701000002"
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
    """Mise à jour du profil bibliothécaire (PATCH)."""
    first_name              = serializers.CharField(max_length=100, required=False)
    last_name               = serializers.CharField(max_length=100, required=False)
    phone                   = serializers.CharField(max_length=17,  required=False)
    date_of_birth           = serializers.DateField(required=False, allow_null=True)
    badge_number            = serializers.CharField(max_length=20,  required=False, allow_null=True)
    date_prise_poste        = serializers.DateField(required=False, allow_null=True)
    peut_gerer_documents    = serializers.BooleanField(required=False)
    peut_gerer_utilisateurs = serializers.BooleanField(required=False)

    def validate_phone(self, value):
        phone = re.sub(r'\s+', '', value)
        if not re.match(r'^\+?[\d]{8,15}$', phone):
            raise serializers.ValidationError("Numéro invalide.")
        return phone


# =============================================================================
# 📤  SERIALIZERS DE RÉPONSE (lecture)
# =============================================================================

class EtudiantDetailSerializer(serializers.Serializer):
    """Réponse complète après création/lecture d'un étudiant."""
    id              = serializers.UUIDField(
        help_text="UUID du profil etudiant. A utiliser dans /api/etudiants/{etudiant_id}/."
    )
    user_id         = serializers.UUIDField(
        source='user.id',
        help_text="UUID du compte utilisateur lie."
    )
    matricule       = serializers.CharField()
    email           = serializers.EmailField(source='user.email')
    first_name      = serializers.CharField(source='user.first_name')
    last_name       = serializers.CharField(source='user.last_name')
    phone           = serializers.CharField(source='user.phone')
    is_active       = serializers.BooleanField(source='user.is_active')
    is_2fa_enabled  = serializers.BooleanField(source='user.is_2fa_enabled')
    filiere         = serializers.SerializerMethodField()
    niveau          = serializers.SerializerMethodField()
    specialite      = serializers.SerializerMethodField()
    annee_inscription   = serializers.IntegerField()
    statut_compte       = serializers.CharField()
    jours_restants      = serializers.IntegerField(allow_null=True)
    pourcentage_validite= serializers.IntegerField(allow_null=True)
    compte_active_le    = serializers.DateTimeField(allow_null=True)
    compte_expire_le    = serializers.DateTimeField(allow_null=True)
    nb_reactivations    = serializers.IntegerField()
    created_at          = serializers.DateTimeField()

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


class BibliothecaireDetailSerializer(serializers.Serializer):
    """Réponse complète après création/lecture d'un bibliothécaire."""
    id                      = serializers.UUIDField(
        help_text="UUID du profil bibliothecaire. A utiliser dans /api/bibliothecaires/{biblio_id}/."
    )
    user_id                 = serializers.UUIDField(
        source='user.id',
        help_text="UUID du compte utilisateur lie."
    )
    email                   = serializers.EmailField(source='user.email')
    first_name              = serializers.CharField(source='user.first_name')
    last_name               = serializers.CharField(source='user.last_name')
    phone                   = serializers.CharField(source='user.phone')
    is_active               = serializers.BooleanField(source='user.is_active')
    is_2fa_enabled          = serializers.BooleanField(source='user.is_2fa_enabled')
    badge_number            = serializers.CharField(allow_null=True)
    date_prise_poste        = serializers.DateField(allow_null=True)
    peut_gerer_documents    = serializers.BooleanField()
    peut_gerer_utilisateurs = serializers.BooleanField()
    created_at              = serializers.DateTimeField()
