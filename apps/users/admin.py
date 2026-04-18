"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — admin.py
 Enregistrement complet de tous les modèles dans l'interface Django Admin
=============================================================================
 Emplacement : apps/admin.py  ou  chaque app/admin.py selon votre structure
=============================================================================
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db import connection
from django.db.models import Count, IntegerField, Q, Value
from django.utils import timezone

from apps.users.models import User, Etudiant, Bibliothecaire, PersonneExterne
from apps.documents.models import ECUE, Document, Filiere, Niveau, TypeDocument, UE
from apps.consultations.models import Consultation
from apps.specialites.models import Specialite
from apps.users.models import CodeVerification


# =============================================================================
# ⚙️  CONFIGURATION GLOBALE DU SITE ADMIN
# =============================================================================

admin.site.site_header  = "📚 Bibliothèque Universitaire — Administration"
admin.site.site_title   = "Bibliothèque Admin"
admin.site.index_title  = "Tableau de bord"


# =============================================================================
# 🎨  MIXINS RÉUTILISABLES
# =============================================================================

class ReadOnlyFieldsMixin:
    """Rend tous les champs en lecture seule (pour les logs et audits)."""
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


class ExportCsvMixin:
    """Ajoute une action d'export CSV à n'importe quel ModelAdmin."""
    actions = ['export_csv']

    @admin.action(description="📥 Exporter la sélection en CSV")
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        meta     = self.model._meta
        fields   = [f.name for f in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.csv'

        writer = csv.writer(response)
        writer.writerow(fields)
        for obj in queryset:
            writer.writerow([getattr(obj, f) for f in fields])
        return response


# =============================================================================
# 👤  UTILISATEUR
# =============================================================================

class EtudiantInline(admin.StackedInline):
    """Profil étudiant affiché directement dans la fiche utilisateur."""
    model          = Etudiant
    fk_name        = 'user'
    can_delete     = False
    verbose_name   = "Profil Étudiant"
    fields         = (
        'filiere',
        'niveau',
        'specialite',
        'annee_inscription',
        'date_debut_validite',
        'date_fin_validite',
    )
    autocomplete_fields = ('filiere', 'niveau', 'specialite')
    extra          = 0


class BibliothacaireInline(admin.StackedInline):
    """Profil bibliothécaire affiché directement dans la fiche utilisateur."""
    model          = Bibliothecaire
    can_delete     = False
    verbose_name   = "Profil Bibliothécaire"
    fields         = ('badge_number', 'date_prise_poste',
                      'peut_gerer_documents', 'peut_gerer_utilisateurs')
    extra          = 0


class PersonneExterneInline(admin.StackedInline):
    """Profil personne externe affiche directement dans la fiche utilisateur."""
    model = PersonneExterne
    can_delete = False
    verbose_name = "Profil Personne Externe"
    fields = (
        'numero_piece',
        'profession',
        'lieu_habitation',
        'date_debut_validite',
        'date_fin_validite',
    )
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin, ExportCsvMixin):
    """
    Administration complète des utilisateurs.
    Connexion par email, gestion 2FA, matricule auto.
    """

    # ── Affichage liste ───────────────────────────────────────────────────────
    list_display = (
        'email', 'full_name', 'user_type_badge','phone', 'statut_2fa', 'is_active_badge', 'created_at'
    )
    list_filter  = ('user_type', 'is_active', 'is_2fa_enabled', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering     = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page  = 25

    # ── Inline profils ────────────────────────────────────────────────────────
    inlines = [EtudiantInline, BibliothacaireInline, PersonneExterneInline]

    # ── Formulaire détail ─────────────────────────────────────────────────────
    fieldsets = (
        (_("🔑 Identifiants"), {
            'fields': ('email', 'password', 'phone')
        }),
        (_("👤 Informations personnelles"), {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'avatar')
        }),
        (_("🏷️ Rôle"), {
            'fields': ('user_type',)
        }),
        (_("🔐 Sécurité 2FA"), {
            'fields': ('is_2fa_enabled', 'totp_secret', 'totp_verified_at'),
            'classes': ('collapse',),
            'description': "Google Authenticator — obligatoire pour Admin et Bibliothécaire."
        }),
        (_("⚙️ Permissions"), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_("📅 Dates"), {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Formulaire création ───────────────────────────────────────────────────
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'phone',
                'user_type', 'password1', 'password2'
            ),
        }),
    )

    readonly_fields = ( 'created_at', 'updated_at', 'totp_verified_at', 'last_login')

    # ── Colonnes personnalisées ───────────────────────────────────────────────

    @admin.display(description="Nom complet")
    def full_name(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="Type")
    def user_type_badge(self, obj):
        colors = {
            'ETUDIANT':       '#28a745',
            'BIBLIOTHECAIRE': '#007bff',
            'ADMINISTRATEUR': '#dc3545',
        }
        color = colors.get(obj.user_type, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;'
            'border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_user_type_display()
        )

    @admin.display(description="2FA", boolean=False)
    def statut_2fa(self, obj):
        if obj.is_2fa_enabled:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">{}</span>',
                '✅ Activé',
            )
        if obj.requires_2fa:
            return format_html(
                '<span style="color:#dc3545;font-weight:bold;">{}</span>',
                '⚠️ Requis',
            )
        return format_html('<span style="color:#6c757d;">{}</span>', '—')

    @admin.display(description="Actif", boolean=False)
    def is_active_badge(self, obj):
        return format_html(
            '<span style="color:{};">{}</span>',
            '#28a745' if obj.is_active else '#dc3545',
            '● Actif' if obj.is_active else '● Inactif'
        )

    # ── Actions ───────────────────────────────────────────────────────────────
    actions = ['activer_comptes', 'desactiver_comptes', 'export_csv']

    @admin.action(description="✅ Activer les comptes sélectionnés")
    def activer_comptes(self, request, queryset):
        nb = 0
        for user in queryset.select_related(
            'profil_etudiant',
            'profil_personne_externe',
        ):
            if hasattr(user, 'profil_etudiant'):
                profil = user.profil_etudiant
                if profil.compte_active_le:
                    profil.reactiver_compte(effectue_par=request.user)
                else:
                    profil.activer_compte(effectue_par=request.user)
                nb += 1
                continue

            if hasattr(user, 'profil_personne_externe'):
                user.profil_personne_externe.activer_compte()
                nb += 1
                continue

            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active', 'updated_at'])
                nb += 1
        self.message_user(request, f"{nb} compte(s) activé(s).")

    @admin.action(description="🚫 Désactiver les comptes sélectionnés")
    def desactiver_comptes(self, request, queryset):
        nb = 0
        for user in queryset.exclude(id=request.user.id).select_related(
            'profil_etudiant',
            'profil_personne_externe',
        ):
            if hasattr(user, 'profil_etudiant'):
                user.profil_etudiant.desactiver_compte(manuel=True)
                nb += 1
                continue

            if hasattr(user, 'profil_personne_externe'):
                user.profil_personne_externe.desactiver_compte(manuel=True)
                nb += 1
                continue

            if user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active', 'updated_at'])
                nb += 1
        self.message_user(request, f"{nb} compte(s) désactivé(s).")


# =============================================================================
# 🎓  ÉTUDIANT
# =============================================================================

@admin.register(Etudiant)
class EtudiantAdmin(ExportCsvMixin, admin.ModelAdmin):

    list_display  = (
        'user_email',
        'user_nom',
        'matricule',
        'filiere',
        'niveau',
        'specialite',
        'annee_inscription',
        'date_debut_validite',
        'date_fin_validite',
    )
    list_filter   = (
        'filiere',
        'niveau',
        'specialite',
        'annee_inscription',
        'date_debut_validite',
        'date_fin_validite',
    )
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'matricule', 'specialite__name')
    autocomplete_fields = ('user', 'filiere', 'niveau', 'specialite')
    list_select_related = ('user', 'filiere', 'niveau', 'specialite')
    ordering      = ('user__last_name',)
    list_per_page = 25

    @admin.display(description="Email", ordering='user__email')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Nom complet", ordering='user__last_name')
    def user_nom(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Matricule")
    def matricule(self, obj):
        return obj.matricule or "—"


@admin.register(PersonneExterne)
class PersonneExterneAdmin(ExportCsvMixin, admin.ModelAdmin):

    list_display = (
        'user_email',
        'user_nom',
        'numero_piece',
        'profession',
        'date_debut_validite',
        'date_fin_validite',
    )
    list_filter = ('date_debut_validite', 'date_fin_validite')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'numero_piece', 'profession')
    autocomplete_fields = ('user',)
    list_select_related = ('user',)
    ordering = ('user__last_name',)
    list_per_page = 25

    @admin.display(description="Email", ordering='user__email')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Nom complet", ordering='user__last_name')
    def user_nom(self, obj):
        return obj.user.get_full_name()


# =============================================================================
# 📖  BIBLIOTHÉCAIRE
# =============================================================================

@admin.register(Bibliothecaire)
class BibliothacaireAdmin(admin.ModelAdmin):

    list_display  = (
        'user_email', 'user_nom', 'badge_number',
        'perm_documents', 'perm_utilisateurs', 'date_prise_poste'
    )
    list_filter   = ('peut_gerer_documents', 'peut_gerer_utilisateurs')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'badge_number')
    autocomplete_fields = ('user',)
    list_per_page = 25

    @admin.display(description="Email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Nom complet")
    def user_nom(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="📄 Documents", boolean=True)
    def perm_documents(self, obj):
        return obj.peut_gerer_documents

    @admin.display(description="👥 Utilisateurs", boolean=True)
    def perm_utilisateurs(self, obj):
        return obj.peut_gerer_utilisateurs


# =============================================================================
# 🏫  FILIÈRE
# =============================================================================

class NiveauInline(admin.TabularInline):
    model   = Niveau
    extra   = 1
    fields  = ('name',)


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):

    list_display   = ('name', 'nb_niveaux', 'nb_etudiants', 'created_at')
    search_fields  = ('name',)
    inlines        = [NiveauInline]
    list_per_page  = 20

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _nb_niveaux   = Count('niveaux', distinct=True),
            _nb_etudiants = Count('etudiants', distinct=True),
        )

    @admin.display(description="Niveaux", ordering='_nb_niveaux')
    def nb_niveaux(self, obj):
        return obj._nb_niveaux

    @admin.display(description="Étudiants", ordering='_nb_etudiants')
    def nb_etudiants(self, obj):
        return obj._nb_etudiants


# =============================================================================
# 📊  NIVEAU
# =============================================================================

@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):

    list_display   = ('filiere', 'name', 'nb_specialites', 'nb_etudiants', 'nb_documents')
    list_filter    = ('filiere', 'name')
    search_fields  = ('filiere__name', 'name')
    autocomplete_fields = ('filiere',)
    list_per_page  = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _nb_specialites = Count('specialites', distinct=True),
            _nb_etudiants = Count('etudiants', distinct=True),
            _nb_documents = Count('documents', distinct=True),
        )

    @admin.display(description="Étudiants")
    def nb_etudiants(self, obj):
        return obj._nb_etudiants

    @admin.display(description="Specialites")
    def nb_specialites(self, obj):
        return obj._nb_specialites

    @admin.display(description="Documents")
    def nb_documents(self, obj):
        return obj._nb_documents


# =============================================================================
# 📚  UE — UNITÉ D'ENSEIGNEMENT
# =============================================================================
@admin.register(Specialite)
class SpecialiteAdmin(admin.ModelAdmin):

    list_display = ('name', 'niveau', 'filiere', 'nb_etudiants', 'nb_documents', 'created_at')
    list_filter = ('niveau__name', 'niveau__filiere')
    search_fields = ('name', 'niveau__name', 'niveau__filiere__name')
    autocomplete_fields = ('niveau',)
    list_select_related = ('niveau', 'niveau__filiere')
    ordering = ('niveau__filiere__name', 'niveau__name', 'name')
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _nb_etudiants=Count('etudiants', distinct=True),
            _nb_documents=Count('documents', distinct=True),
        )

    @admin.display(description="Filiere", ordering='niveau__filiere__name')
    def filiere(self, obj):
        return obj.niveau.filiere

    @admin.display(description="Etudiants", ordering='_nb_etudiants')
    def nb_etudiants(self, obj):
        return obj._nb_etudiants

    @admin.display(description="Documents", ordering='_nb_documents')
    def nb_documents(self, obj):
        return obj._nb_documents


class ECUEInline(admin.TabularInline):
    model = ECUE
    extra = 1
    fields = ('code', 'name', 'coef')
    show_change_link = True


@admin.register(UE)
class UEAdmin(admin.ModelAdmin):

    list_display   = ('code', 'name', 'coef', 'nb_ecues', 'nb_documents', 'niveaux_list')
    search_fields  = ('code', 'name')
    filter_horizontal = ('niveaux',)
    readonly_fields = ('coef',)
    inlines = [ECUEInline]
    list_per_page  = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _nb_documents = Count('ecues__documents', distinct=True),
            _nb_ecues = Count('ecues', distinct=True),
        )

    @admin.display(description="Coefficient total")
    def coef(self, obj):
        return obj.coef_total

    @admin.display(description="ECUE")
    def nb_ecues(self, obj):
        return obj._nb_ecues

    @admin.display(description="Documents")
    def nb_documents(self, obj):
        return obj._nb_documents

    @admin.display(description="Niveaux")
    def niveaux_list(self, obj):
        niveaux = obj.niveaux.all()[:3]
        noms    = ", ".join(str(n) for n in niveaux)
        if obj.niveaux.count() > 3:
            noms += f" +{obj.niveaux.count() - 3}"
        return noms or "—"


# =============================================================================
# 📄  DOCUMENT
# =============================================================================

@admin.register(ECUE)
class ECUEAdmin(admin.ModelAdmin):

    list_display = ('code', 'name', 'ue', 'coef', 'created_at')
    search_fields = ('code', 'name', 'ue__code', 'ue__name')
    autocomplete_fields = ('ue',)
    list_select_related = ('ue',)
    ordering = ('ue__code', 'code')


@admin.register(Document)
class DocumentAdmin(ExportCsvMixin, admin.ModelAdmin):

    list_display   = (
        'title', 'type_badge', 'annee_academique_display', 'filiere', 'niveau', 'specialite', 'ue',
        'auteur_ou_encadreur', 'ajoute_par', 'nb_consultations', 'nb_favoris', 'created_at'
    )
    list_filter    = ('type', 'annee_academique_debut', 'filiere', 'niveau', 'specialite', 'ue', 'created_at')
    search_fields  = ('title', 'auteur', 'encadreur', 'description', 'specialite__name', 'ue__code', 'ue__name')
    autocomplete_fields = ('filiere', 'niveau', 'specialite', 'ue', 'ajoute_par')
    list_select_related = ('filiere', 'niveau', 'specialite', 'ue', 'ajoute_par')
    date_hierarchy = 'created_at'
    ordering       = ('-annee_academique_debut', '-created_at')
    list_per_page  = 20

    fieldsets = (
        (_("📋 Informations générales"), {
            'fields': ('title', 'type', 'annee_academique_debut', 'description', 'file_name', 'file_mime_type', 'file_base64')
        }),
        (_("🏫 Classification"), {
            'fields': ('filiere', 'niveau', 'specialite', 'ue')
        }),
        (_("✍️ Auteur / Encadreur"), {
            'fields': ('auteur', 'encadreur'),
            'description': "Memoire/These : renseigner l'auteur. Cours/Examen : renseigner l'encadreur ou le sujet."
        }),
        (_("👤 Ajouté par"), {
            'fields': ('ajoute_par',)
        }),
        (_("📅 Dates"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        tables = set(connection.introspection.table_names())
        annotations = {}

        # Some project tables may not exist yet while the admin is already in use.
        # In that case, keep the page functional and show zero instead of crashing.
        if 'consultations_consultation' in tables:
            annotations['_nb_consultations'] = Count('consultations', distinct=True)
        else:
            annotations['_nb_consultations'] = Value(0, output_field=IntegerField())

        if 'favoris_favori' in tables:
            annotations['_nb_favoris'] = Count('mis_en_favori_par', distinct=True)
        else:
            annotations['_nb_favoris'] = Value(0, output_field=IntegerField())

        return super().get_queryset(request).annotate(**annotations)

    @admin.display(description="Type")
    def type_badge(self, obj):
        colors = {
            'EXAMEN':  '#fd7e14',
            'MEMOIRE': '#6f42c1',
            'THESE':   '#dc3545',
            'COURS':   '#007bff',
        }
        color = colors.get(obj.type, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;">{}</span>',
            color, obj.get_type_display()
        )

    @admin.display(description="Annee academique", ordering='annee_academique_debut')
    def annee_academique_display(self, obj):
        return obj.annee_academique or "—"

    @admin.display(description="Auteur / Sujet")
    def auteur_ou_encadreur(self, obj):
        if obj.type in {TypeDocument.MEMOIRE, TypeDocument.THESE}:
            return obj.auteur or "—"
        return obj.encadreur or "—"

    @admin.display(description="👁 Vues", ordering='_nb_consultations')
    def nb_consultations(self, obj):
        return obj._nb_consultations

    @admin.display(description="⭐ Favoris", ordering='_nb_favoris')
    def nb_favoris(self, obj):
        return obj._nb_favoris

    # ── Actions ───────────────────────────────────────────────────────────────
    actions = ['export_csv']


# =============================================================================
# 👁️  CONSULTATION
# =============================================================================

@admin.register(Consultation)
class ConsultationAdmin(ReadOnlyFieldsMixin, admin.ModelAdmin):
    """
    Lecture seule — les consultations ne doivent pas être modifiées manuellement.
    """

    list_display   = (
        'user', 'type_badge', 'document_titre', 'recherche_query',
        'duree_formatee', 'ip_address', 'created_at'
    )
    list_filter    = ('type_consultation', 'created_at')
    search_fields  = ('user__email', 'document__title', 'recherche_query', 'ip_address')
    date_hierarchy = 'created_at'
    ordering       = ('-created_at',)
    list_per_page  = 30

    @admin.display(description="Type")
    def type_badge(self, obj):
        colors = {
            'VUE':       '#007bff',
            'RECHERCHE': '#28a745',
        }
        color = colors.get(obj.type_consultation, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;">{}</span>',
            color, obj.get_type_consultation_display()
        )

    @admin.display(description="Document")
    def document_titre(self, obj):
        if obj.document:
            return obj.document.title[:50]
        return "—"

    @admin.display(description="Durée")
    def duree_formatee(self, obj):
        return obj.duree_formatee


# =============================================================================
# 🔐  CODE DE VÉRIFICATION
# =============================================================================

@admin.register(CodeVerification)
class CodeVerificationAdmin(ReadOnlyFieldsMixin, admin.ModelAdmin):
    """
    Lecture seule — audit des codes OTP envoyés.
    """

    list_display  = (
        'user', 'type_code', 'email', 'statut_badge',
        'attempts', 'max_attempts', 'expires_at', 'created_at'
    )
    list_filter   = ('type_code', 'is_used', 'created_at')
    search_fields = ('user__email', 'email', 'code')
    date_hierarchy = 'created_at'
    ordering      = ('-created_at',)
    list_per_page = 30

    @admin.display(description="Statut")
    def statut_badge(self, obj):
        if obj.is_used:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">{}</span>',
                '✅ Utilisé',
            )
        if obj.is_expired():
            return format_html(
                '<span style="color:#dc3545;font-weight:bold;">{}</span>',
                '⏰ Expiré',
            )
        if obj.attempts >= obj.max_attempts:
            return format_html(
                '<span style="color:#fd7e14;font-weight:bold;">{}</span>',
                '🚫 Bloqué',
            )
        return format_html(
            '<span style="color:#007bff;font-weight:bold;">{}</span>',
            '⏳ En attente',
        )


"""
=============================================================================
 BIBLIOTHÈQUE UNIVERSITAIRE — admin_favoris_historique.py
 Admin : Favori (PostgreSQL) + HistoriqueAction (MongoDB via PyMongo)
=============================================================================
 À fusionner dans votre admin.py principal ou importer séparément.
=============================================================================
"""

from django.contrib import admin
from django.utils.html import format_html
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from django.db.models import Count

from apps.documents.models import Document
from apps.favoris.models import Favori
from apps.users.models.etudiant_models import Etudiant
from apps.users.models.user_models import User


# =============================================================================
# ⭐  FAVORI (PostgreSQL)
# =============================================================================

@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    """
    Administration des favoris — lecture + statistiques.
    Permet de voir qui a mis quoi en favori et depuis quand.
    """

    # ── Liste ─────────────────────────────────────────────────────────────────
    list_display = (
        'etudiant_nom', 'etudiant_matricule', 'document_titre',
        'document_type_badge', 'document_ue', 'created_at'
    )
    list_filter  = (
        'document__type',
        'document__filiere',
        'document__niveau',
        'created_at',
    )
    search_fields = (
        'etudiant__user__email',
        'etudiant__user__first_name',
        'etudiant__user__last_name',
        'etudiant__matricule',
        'document__title',
        'document__ue__code',
    )
    date_hierarchy  = 'created_at'
    ordering        = ('-created_at',)
    list_per_page   = 30
    list_select_related = ('etudiant__user', 'document__ue', 'document__filiere')

    # ── Formulaire détail ─────────────────────────────────────────────────────
    fieldsets = (
        ("⭐ Favori", {
            'fields': ('etudiant', 'document', 'created_at')
        }),
    )
    readonly_fields = ('created_at',)
    autocomplete_fields = ('etudiant', 'document')

    # ── Colonnes personnalisées ───────────────────────────────────────────────

    @admin.display(description="Étudiant", ordering='etudiant__user__last_name')
    def etudiant_nom(self, obj):
        return obj.etudiant.user.get_full_name()

    @admin.display(description="Matricule")
    def etudiant_matricule(self, obj):
        return format_html(
            '<code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;">{}</code>',
            obj.etudiant.matricule or '—'
        )

    @admin.display(description="Document", ordering='document__title')
    def document_titre(self, obj):
        return obj.document.title[:55] + ('…' if len(obj.document.title) > 55 else '')

    @admin.display(description="Type")
    def document_type_badge(self, obj):
        colors = {
            'EXAMEN':  '#fd7e14',
            'MEMOIRE': '#6f42c1',
            'THESE':   '#dc3545',
            'COURS':   '#007bff',
        }
        color = colors.get(obj.document.type, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.document.get_type_display()
        )

    @admin.display(description="UE")
    def document_ue(self, obj):
        if obj.document.ue:
            return format_html(
                '<span style="font-family:monospace;font-size:12px;">{}</span>',
                obj.document.ue.code
            )
        return '—'

    # ── Actions ───────────────────────────────────────────────────────────────
    actions = ['export_csv_favoris']

    @admin.action(description="📥 Exporter les favoris sélectionnés en CSV")
    def export_csv_favoris(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="favoris_2025.csv"'
        response.write('\ufeff')  # BOM UTF-8 pour Excel

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Étudiant', 'Matricule', 'Email', 'Filière', 'Niveau',
            'Document', 'Type', 'UE', 'Date ajout favori'
        ])
        for fav in queryset.select_related(
            'etudiant__user', 'etudiant__filiere', 'etudiant__niveau',
            'document__ue'
        ):
            writer.writerow([
                fav.etudiant.user.get_full_name(),
                fav.etudiant.matricule or '',
                fav.etudiant.user.email,
                str(fav.etudiant.filiere or ''),
                str(fav.etudiant.niveau or ''),
                fav.document.title,
                fav.document.get_type_display(),
                fav.document.ue.code if fav.document.ue else '',
                fav.created_at.strftime('%d/%m/%Y %H:%M'),
            ])
        return response

    # ── Changelist avec stats en haut ─────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Top 5 documents les plus mis en favoris
        top_docs = (
            Favori.objects
            .values('document__title', 'document__type')
            .annotate(nb=Count('id'))
            .order_by('-nb')[:5]
        )

        # Top 3 étudiants avec le plus de favoris
        top_etus = (
            Favori.objects
            .values(
                'etudiant__user__first_name',
                'etudiant__user__last_name',
                'etudiant__matricule',
            )
            .annotate(nb=Count('id'))
            .order_by('-nb')[:3]
        )

        extra_context['top_documents_favoris'] = list(top_docs)
        extra_context['top_etudiants_favoris']  = list(top_etus)
        extra_context['total_favoris']           = Favori.objects.count()
        return super().changelist_view(request, extra_context=extra_context)


# =============================================================================
# 📋  HISTORIQUE ACTION (MongoDB) — Vue Admin personnalisée
# =============================================================================

class HistoriqueActionAdmin(admin.ModelAdmin):
    """
    Pseudo-ModelAdmin pour afficher les logs MongoDB dans l'interface Django Admin.
    Utilise une vue personnalisée basée sur PyMongo.

    ⚠️  Ce ModelAdmin ne correspond à AUCUN modèle Django ORM.
        Il est enregistré avec un modèle proxy léger (voir HistoriqueActionProxy).
    """
    change_list_template = 'admin/historique_action_list.html'

    class Media:
        css = {'all': ('admin/css/historique.css',)}

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'api/historique/',
                self.admin_site.admin_view(self.api_historique),
                name='historique_action_api'
            ),
            path(
                'api/historique/stats/',
                self.admin_site.admin_view(self.api_stats),
                name='historique_action_stats'
            ),
        ]
        return custom + urls

    def api_historique(self, request):
        """
        API JSON pour charger les logs MongoDB via AJAX dans l'admin.
        Paramètres GET : action, user_id, statut, limit (défaut 50)
        """
        from apps.history.models import HistoriqueActionService as HAS
        from core.mongo_client import get_collection

        col    = get_collection('historique_actions')
        filtres = {}

        action  = request.GET.get('action')
        user_id = request.GET.get('user_id')
        statut  = request.GET.get('statut')
        limit   = min(int(request.GET.get('limit', 50)), 200)

        if action:
            filtres['action'] = action
        if user_id:
            filtres['user_id'] = user_id
        if statut:
            filtres['statut'] = statut

        docs = list(col.find(filtres, sort=[('created_at', -1)], limit=limit))
        data = [HAS._serialize(d) for d in docs]
        return JsonResponse({'results': data, 'count': len(data)})

    def api_stats(self, request):
        """Statistiques agrégées des actions pour le tableau de bord."""
        from core.mongo_client import get_collection
        from datetime import timedelta

        col    = get_collection('historique_actions')
        depuis = timezone.now() - timedelta(days=30)

        pipeline = [
            {'$match': {'created_at': {'$gte': depuis}}},
            {'$group': {
                '_id':    '$action',
                'total':  {'$sum': 1},
                'echecs': {'$sum': {'$cond': [{'$eq': ['$statut', 'echec']}, 1, 0]}}
            }},
            {'$sort': {'total': -1}}
        ]
        stats = list(col.aggregate(pipeline))
        for s in stats:
            s['action'] = s.pop('_id')

        return JsonResponse({'stats': stats, 'periode': '30 derniers jours'})

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ── Modèle proxy léger pour enregistrer HistoriqueActionAdmin ────────────────

class HistoriqueActionProxy(Favori):
    """
    Modèle proxy sans table réelle — sert uniquement à accrocher
    HistoriqueActionAdmin à l'interface Django Admin.
    """
    class Meta:
        proxy        = True
        managed      = False
        verbose_name = "Historique Action (MongoDB)"
        verbose_name_plural = "Historiques Actions (MongoDB)"
        app_label    = 'documents'




# =============================================================================
# 📊  TEMPLATE ADMIN INLINE — à créer dans templates/admin/
# =============================================================================

"""
Créez le fichier :
  templates/admin/historique_action_list.html

Contenu minimal (étend le template admin de base) :

{% extends "admin/change_list.html" %}
{% block content %}

<div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap;">

  <!-- Filtres rapides -->
  <div style="background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;flex:1;min-width:260px;">
    <h3 style="margin:0 0 12px;color:#333;">🔍 Filtrer les logs</h3>
    <select id="filtre-action" style="width:100%;margin-bottom:8px;padding:6px;">
      <option value="">— Toutes les actions —</option>
      <option value="CONNEXION">Connexion</option>
      <option value="DECONNEXION">Déconnexion</option>
      <option value="CONNEXION_ECHEC">Connexion échouée</option>
      <option value="OTP_ECHEC">OTP échoué</option>
      <option value="TOTP_ACTIVE">TOTP activé</option>
      <option value="DOCUMENT_AJOUT">Document ajouté</option>
      <option value="DOCUMENT_MODIFICATION">Document modifié</option>
      <option value="DOCUMENT_SUPPRESSION">Document supprimé</option>
      <option value="UTILISATEUR_CREATION">Utilisateur créé</option>
      <option value="UTILISATEUR_MODIF">Utilisateur modifié</option>
    </select>
    <select id="filtre-statut" style="width:100%;margin-bottom:8px;padding:6px;">
      <option value="">— Tous les statuts —</option>
      <option value="succes">✅ Succès</option>
      <option value="echec">❌ Échec</option>
    </select>
    <button onclick="chargerLogs()" style="background:#417690;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;width:100%;">
      Charger les logs
    </button>
  </div>

  <!-- Stats -->
  <div style="background:#fff;border:1px solid #ddd;border-radius:8px;padding:16px;flex:1;min-width:260px;" id="stats-box">
    <h3 style="margin:0 0 12px;color:#333;">📊 Stats 30 derniers jours</h3>
    <p style="color:#999;font-style:italic;">Cliquez sur "Charger les logs"...</p>
  </div>
</div>

<!-- Table des logs -->
<div style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;font-size:13px;" id="logs-table">
    <thead style="background:#417690;color:#fff;">
      <tr>
        <th style="padding:10px 12px;text-align:left;">Date</th>
        <th style="padding:10px 12px;text-align:left;">Action</th>
        <th style="padding:10px 12px;text-align:left;">Utilisateur</th>
        <th style="padding:10px 12px;text-align:left;">Type</th>
        <th style="padding:10px 12px;text-align:left;">Statut</th>
        <th style="padding:10px 12px;text-align:left;">IP</th>
        <th style="padding:10px 12px;text-align:left;">Détails</th>
      </tr>
    </thead>
    <tbody id="logs-body">
      <tr><td colspan="7" style="text-align:center;padding:20px;color:#999;">
        Utilisez les filtres ci-dessus pour charger les logs.
      </td></tr>
    </tbody>
  </table>
</div>

<script>
const BADGE_COLORS = {
  CONNEXION:             {bg:'#28a745',label:'Connexion'},
  DECONNEXION:           {bg:'#6c757d',label:'Déconnexion'},
  CONNEXION_ECHEC:       {bg:'#dc3545',label:'Connexion échouée'},
  OTP_ECHEC:             {bg:'#dc3545',label:'OTP échoué'},
  TOTP_ACTIVE:           {bg:'#007bff',label:'TOTP activé'},
  TOTP_ECHEC:            {bg:'#dc3545',label:'TOTP échoué'},
  DOCUMENT_AJOUT:        {bg:'#17a2b8',label:'Doc ajouté'},
  DOCUMENT_MODIFICATION: {bg:'#fd7e14',label:'Doc modifié'},
  DOCUMENT_SUPPRESSION:  {bg:'#dc3545',label:'Doc supprimé'},
  UTILISATEUR_CREATION:  {bg:'#6f42c1',label:'User créé'},
  UTILISATEUR_MODIF:     {bg:'#fd7e14',label:'User modifié'},
  UTILISATEUR_DESACTIVE: {bg:'#dc3545',label:'User désactivé'},
};

async function chargerLogs() {
  const action = document.getElementById('filtre-action').value;
  const statut = document.getElementById('filtre-statut').value;
  let url = "{% url 'admin:historique_action_api' %}?limit=100";
  if (action) url += `&action=${action}`;
  if (statut) url += `&statut=${statut}`;

  const tbody = document.getElementById('logs-body');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;">⏳ Chargement...</td></tr>';

  try {
    const res  = await fetch(url);
    const data = await res.json();
    afficherLogs(data.results);
    chargerStats();
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:red;padding:16px;">❌ Erreur : ${e}</td></tr>`;
  }
}

function afficherLogs(logs) {
  const tbody = document.getElementById('logs-body');
  if (!logs.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#999;">Aucun log trouvé.</td></tr>';
    return;
  }
  tbody.innerHTML = logs.map((log, i) => {
    const badge  = BADGE_COLORS[log.action] || {bg:'#6c757d', label: log.action};
    const statut = log.statut === 'succes'
      ? '<span style="color:#28a745;font-weight:bold;">✅ Succès</span>'
      : '<span style="color:#dc3545;font-weight:bold;">❌ Échec</span>';
    const details = log.details && Object.keys(log.details).length
      ? `<code style="font-size:11px;background:#f5f5f5;padding:2px 4px;">${JSON.stringify(log.details).substring(0,60)}...</code>`
      : '—';
    const bg = i % 2 === 0 ? '#fff' : '#f9f9f9';
    return `<tr style="background:${bg};">
      <td style="padding:8px 12px;white-space:nowrap;font-size:12px;">${log.created_at ? new Date(log.created_at).toLocaleString('fr-FR') : '—'}</td>
      <td style="padding:8px 12px;">
        <span style="background:${badge.bg};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;">${badge.label}</span>
      </td>
      <td style="padding:8px 12px;font-size:12px;">${log.user_email || '<em style="color:#999">Anonyme</em>'}</td>
      <td style="padding:8px 12px;font-size:12px;">${log.user_type || '—'}</td>
      <td style="padding:8px 12px;">${statut}</td>
      <td style="padding:8px 12px;font-family:monospace;font-size:11px;">${log.ip_address || '—'}</td>
      <td style="padding:8px 12px;">${details}</td>
    </tr>`;
  }).join('');
}

async function chargerStats() {
  try {
    const res   = await fetch("{% url 'admin:historique_action_stats' %}");
    const data  = await res.json();
    const box   = document.getElementById('stats-box');
    const rows  = data.stats.map(s =>
      `<tr>
        <td style="padding:4px 8px;">${BADGE_COLORS[s.action]?.label || s.action}</td>
        <td style="padding:4px 8px;font-weight:bold;color:#417690;">${s.total}</td>
        <td style="padding:4px 8px;color:#dc3545;">${s.echecs > 0 ? s.echecs + ' ❌' : '—'}</td>
      </tr>`
    ).join('');
    box.innerHTML = `
      <h3 style="margin:0 0 12px;color:#333;">📊 Stats — ${data.periode}</h3>
      <table style="width:100%;font-size:12px;">
        <thead><tr style="color:#999;">
          <th style="text-align:left;padding:4px 8px;">Action</th>
          <th style="text-align:left;padding:4px 8px;">Total</th>
          <th style="text-align:left;padding:4px 8px;">Échecs</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch(e) { console.warn('Stats MongoDB indisponibles', e); }
}
</script>
{% endblock %}
"""
