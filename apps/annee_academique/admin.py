from django.contrib import admin, messages

from .models import AnneeAcademique


@admin.register(AnneeAcademique)
class AnneeAcademiqueAdmin(admin.ModelAdmin):
    list_display = (
        "libelle",
        "date_debut",
        "date_fin",
        "est_courante",
        "created_at",
    )
    list_filter = ("est_courante", "date_debut", "date_fin")
    readonly_fields = ("id", "libelle", "created_at", "updated_at")
    ordering = ("-date_debut",)
    date_hierarchy = "date_debut"
    list_per_page = 20
    actions = ("marquer_comme_courante",)

    fieldsets = (
        (
            "Informations",
            {
                "fields": (
                    "id",
                    "libelle",
                    "date_debut",
                    "date_fin",
                    "est_courante",
                )
            },
        ),
        (
            "Suivi",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Marquer comme annee courante")
    def marquer_comme_courante(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Veuillez selectionner une seule annee academique.",
                messages.WARNING,
            )
            return

        annee = queryset.first()
        annee.est_courante = True
        annee.save()
        self.message_user(
            request,
            f"L'annee academique {annee.libelle} est maintenant l'annee courante.",
            messages.SUCCESS,
        )
