import json

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html

from apps.history.models import HistoriqueAction, HistoriqueActionService


@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    change_list_template = "admin/historique_action_list.html"
    list_display = (
        "created_at",
        "action_badge",
        "user_email_display",
        "user_type_display",
        "statut_badge",
        "ip_address",
        "details_resume",
    )
    list_filter = ("action", "statut", "user_type", "created_at")
    search_fields = ("user_email", "user__email", "ip_address", "action")
    readonly_fields = (
        "created_at",
        "action",
        "statut",
        "user",
        "user_email",
        "user_type",
        "ip_address",
        "user_agent",
        "details_pretty",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    autocomplete_fields = ("user",)

    fieldsets = (
        (
            "Historique",
            {
                "fields": (
                    "created_at",
                    "action",
                    "statut",
                    "user",
                    "user_email",
                    "user_type",
                    "ip_address",
                    "user_agent",
                    "details_pretty",
                )
            },
        ),
    )

    class Media:
        css = {"all": ("admin/css/historique.css",)}

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "api/historique/",
                self.admin_site.admin_view(self.api_historique),
                name="historique_action_api",
            ),
            path(
                "api/historique/stats/",
                self.admin_site.admin_view(self.api_stats),
                name="historique_action_stats",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["action_choices"] = HistoriqueAction.Action.choices
        return super().changelist_view(request, extra_context=extra_context)

    @staticmethod
    def _safe_limit(raw_limit: str | None, default: int = 50, maximum: int = 200) -> int:
        try:
            limit = int(raw_limit or default)
        except (TypeError, ValueError):
            limit = default
        return min(max(limit, 1), maximum)

    def api_historique(self, request):
        queryset = self.get_queryset(request)

        action = request.GET.get("action")
        user_id = request.GET.get("user_id")
        statut = request.GET.get("statut")
        limit = self._safe_limit(request.GET.get("limit"))

        if action:
            queryset = queryset.filter(action=action)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if statut:
            queryset = queryset.filter(statut=statut)

        logs = [HistoriqueActionService._serialize(log) for log in queryset[:limit]]
        return JsonResponse({"results": logs, "count": len(logs)})

    def api_stats(self, request):
        stats = HistoriqueActionService.get_stats(days=30)
        return JsonResponse({"stats": stats, "periode": "30 derniers jours"})

    def get_model_perms(self, request):
        if not request.user.is_staff:
            return {}
        return {"add": False, "change": False, "delete": False, "view": True}

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Action", ordering="action")
    def action_badge(self, obj):
        colors = {
            HistoriqueAction.Action.CONNEXION_ETAPE_1: "#17a2b8",
            HistoriqueAction.Action.CONNEXION: "#28a745",
            HistoriqueAction.Action.DECONNEXION: "#6c757d",
            HistoriqueAction.Action.CONNEXION_ECHEC: "#dc3545",
            HistoriqueAction.Action.OTP_ENVOI: "#007bff",
            HistoriqueAction.Action.OTP_ECHEC: "#dc3545",
            HistoriqueAction.Action.TOTP_ACTIVE: "#007bff",
            HistoriqueAction.Action.TOTP_ECHEC: "#dc3545",
            HistoriqueAction.Action.DOCUMENT_AJOUT: "#17a2b8",
            HistoriqueAction.Action.DOCUMENT_MODIFICATION: "#fd7e14",
            HistoriqueAction.Action.DOCUMENT_SUPPRESSION: "#dc3545",
            HistoriqueAction.Action.UTILISATEUR_CREATION: "#6f42c1",
            HistoriqueAction.Action.UTILISATEUR_MODIF: "#fd7e14",
            HistoriqueAction.Action.UTILISATEUR_DESACTIVE: "#dc3545",
            HistoriqueAction.Action.UTILISATEUR_SUPPRIME: "#5a1e1e",
            HistoriqueAction.Action.FAVORI_AJOUT: "#e83e8c",
            HistoriqueAction.Action.FAVORI_SUPPRESSION: "#a61e4d",
            HistoriqueAction.Action.CONSULTATION_VUE: "#20c997",
            HistoriqueAction.Action.CONSULTATION_RECHERCHE: "#6610f2",
            HistoriqueAction.Action.CONSULTATION_TERMINEE: "#0d6efd",
        }
        color = colors.get(obj.action, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            color,
            obj.action_label,
        )

    @admin.display(description="Utilisateur", ordering="user_email")
    def user_email_display(self, obj):
        return obj.user_email or "Anonyme"

    @admin.display(description="Type", ordering="user_type")
    def user_type_display(self, obj):
        return obj.user_type or "-"

    @admin.display(description="Statut", ordering="statut")
    def statut_badge(self, obj):
        color = "#28a745" if obj.statut == HistoriqueAction.Statut.SUCCES else "#dc3545"
        label = "Succes" if obj.statut == HistoriqueAction.Statut.SUCCES else "Echec"
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Details")
    def details_resume(self, obj):
        payload = json.dumps(obj.details or {}, ensure_ascii=False)
        if len(payload) > 80:
            payload = f"{payload[:77]}..."
        return payload or "-"

    @admin.display(description="Details")
    def details_pretty(self, obj):
        payload = json.dumps(obj.details or {}, ensure_ascii=False, indent=2)
        return format_html(
            '<pre style="white-space:pre-wrap;margin:0;font-family:monospace;">{}</pre>',
            payload,
        )
