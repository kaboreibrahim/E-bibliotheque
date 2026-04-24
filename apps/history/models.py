import json
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class HistoriqueAction(models.Model):
    class Statut(models.TextChoices):
        SUCCES = "succes", "Succes"
        ECHEC = "echec", "Echec"

    class Action(models.TextChoices):
        CONNEXION_ETAPE_1 = "CONNEXION_ETAPE_1", "Connexion etape 1"
        CONNEXION = "CONNEXION", "Connexion"
        DECONNEXION = "DECONNEXION", "Deconnexion"
        CONNEXION_ECHEC = "CONNEXION_ECHEC", "Connexion echouee"
        OTP_ENVOI = "OTP_ENVOI", "OTP envoye"
        OTP_ECHEC = "OTP_ECHEC", "OTP echoue"
        TOTP_ACTIVE = "TOTP_ACTIVE", "TOTP valide"
        TOTP_ECHEC = "TOTP_ECHEC", "TOTP echoue"
        DOCUMENT_AJOUT = "DOCUMENT_AJOUT", "Document ajoute"
        DOCUMENT_MODIFICATION = "DOCUMENT_MODIFICATION", "Document modifie"
        DOCUMENT_SUPPRESSION = "DOCUMENT_SUPPRESSION", "Document supprime"
        UTILISATEUR_CREATION = "UTILISATEUR_CREATION", "Utilisateur cree"
        UTILISATEUR_MODIF = "UTILISATEUR_MODIF", "Utilisateur modifie"
        UTILISATEUR_DESACTIVE = "UTILISATEUR_DESACTIVE", "Utilisateur desactive"
        UTILISATEUR_SUPPRIME = "UTILISATEUR_SUPPRIME", "Utilisateur supprime"
        FAVORI_AJOUT = "FAVORI_AJOUT", "Favori ajoute"
        FAVORI_SUPPRESSION = "FAVORI_SUPPRESSION", "Favori supprime"
        CONSULTATION_VUE = "CONSULTATION_VUE", "Consultation document"
        CONSULTATION_RECHERCHE = "CONSULTATION_RECHERCHE", "Recherche effectuee"
        CONSULTATION_TERMINEE = "CONSULTATION_TERMINEE", "Consultation terminee"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
        verbose_name="Action",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historique_actions",
        verbose_name="Utilisateur",
    )
    user_email = models.EmailField(blank=True, verbose_name="Email utilisateur")
    user_type = models.CharField(max_length=20, blank=True, verbose_name="Type utilisateur")
    details = models.JSONField(default=dict, blank=True, verbose_name="Details")
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP",
    )
    user_agent = models.CharField(max_length=500, blank=True, verbose_name="User agent")
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.SUCCES,
        db_index=True,
        verbose_name="Statut",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Cree le")

    class Meta:
        verbose_name = "Historique d'action"
        verbose_name_plural = "Historiques d'actions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["statut", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        email = self.user_email or "Anonyme"
        return f"{self.action} - {email} - {self.created_at:%d/%m/%Y %H:%M}"

    @property
    def action_label(self) -> str:
        return dict(self.Action.choices).get(self.action, self.action)


class HistoriqueActionService:
    ACTIONS = HistoriqueAction.Action
    STATUTS = HistoriqueAction.Statut

    @staticmethod
    def _normalize_details(details: dict | None) -> dict:
        if details is None:
            payload = {}
        elif isinstance(details, dict):
            payload = details
        else:
            payload = {"value": details}

        try:
            return json.loads(json.dumps(payload, default=str))
        except TypeError:
            return {"value": str(payload)}

    @staticmethod
    def _truncate_user_agent(user_agent: str | None) -> str:
        return (user_agent or "")[:500]

    @classmethod
    def get_action_label(cls, action: str) -> str:
        return dict(HistoriqueAction.Action.choices).get(action, action)

    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        details: dict | None = None,
        statut: str = HistoriqueAction.Statut.SUCCES,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        try:
            log = HistoriqueAction.objects.create(
                action=action,
                user=user if getattr(user, "pk", None) else None,
                user_email=getattr(user, "email", "") or "",
                user_type=getattr(user, "user_type", "") or "",
                details=cls._normalize_details(details),
                ip_address=ip_address,
                user_agent=cls._truncate_user_agent(user_agent),
                statut=statut,
            )
            return str(log.pk)
        except Exception as exc:
            logger.error("[HistoriqueAction] Impossible d'enregistrer '%s': %s", action, exc)
            return None

    @classmethod
    def log_connexion(
        cls,
        user,
        statut: str = HistoriqueAction.Statut.SUCCES,
        ip: str | None = None,
        ua: str | None = None,
        details: dict | None = None,
    ) -> str | None:
        payload = {"email": getattr(user, "email", None)}
        if details:
            payload.update(details)
        action = cls.ACTIONS.CONNEXION if statut == cls.STATUTS.SUCCES else cls.ACTIONS.CONNEXION_ECHEC
        return cls.log(
            action=action,
            user=user,
            statut=statut,
            ip_address=ip,
            user_agent=ua,
            details=payload,
        )

    @classmethod
    def log_deconnexion(cls, user, ip: str | None = None, ua: str | None = None) -> str | None:
        return cls.log(
            action=cls.ACTIONS.DECONNEXION,
            user=user,
            ip_address=ip,
            user_agent=ua,
        )

    @classmethod
    def log_otp_echec(
        cls,
        user,
        type_otp: str = "email",
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        tentatives = None
        if user:
            try:
                code = user.codes_verification.filter(is_used=False).first()
                tentatives = getattr(code, "attempts", None)
            except Exception:
                tentatives = None

        return cls.log(
            action=cls.ACTIONS.OTP_ECHEC,
            user=user,
            statut=cls.STATUTS.ECHEC,
            ip_address=ip,
            user_agent=ua,
            details={"type_otp": type_otp, "tentatives": tentatives},
        )

    @classmethod
    def log_totp(
        cls,
        user,
        statut: str = HistoriqueAction.Statut.SUCCES,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        action = cls.ACTIONS.TOTP_ACTIVE if statut == cls.STATUTS.SUCCES else cls.ACTIONS.TOTP_ECHEC
        return cls.log(
            action=action,
            user=user,
            statut=statut,
            ip_address=ip,
            user_agent=ua,
        )

    @classmethod
    def log_document(
        cls,
        action_type: str,
        user,
        document,
        details: dict | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        mapping = {
            "AJOUT": cls.ACTIONS.DOCUMENT_AJOUT,
            "MODIFICATION": cls.ACTIONS.DOCUMENT_MODIFICATION,
            "SUPPRESSION": cls.ACTIONS.DOCUMENT_SUPPRESSION,
        }
        payload = {
            "document_id": str(getattr(document, "id", "")) or None,
            "document_titre": getattr(document, "title", None),
            "document_type": getattr(document, "type_code", None),
        }
        if details:
            payload.update(details)
        return cls.log(
            action=mapping.get(action_type, cls.ACTIONS.DOCUMENT_MODIFICATION),
            user=user,
            ip_address=ip,
            user_agent=ua,
            details=payload,
        )

    @classmethod
    def log_utilisateur(
        cls,
        action_type: str,
        auteur,
        cible_user,
        details: dict | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        mapping = {
            "CREATION": cls.ACTIONS.UTILISATEUR_CREATION,
            "MODIF": cls.ACTIONS.UTILISATEUR_MODIF,
            "DESACTIVE": cls.ACTIONS.UTILISATEUR_DESACTIVE,
            "SUPPRIME": cls.ACTIONS.UTILISATEUR_SUPPRIME,
        }
        payload = {
            "cible_id": str(getattr(cible_user, "id", "")) or None,
            "cible_email": getattr(cible_user, "email", None),
            "cible_type": getattr(cible_user, "user_type", None),
        }
        if details:
            payload.update(details)
        return cls.log(
            action=mapping.get(action_type, cls.ACTIONS.UTILISATEUR_MODIF),
            user=auteur,
            ip_address=ip,
            user_agent=ua,
            details=payload,
        )

    @classmethod
    def log_favori(
        cls,
        action_type: str,
        user,
        favori=None,
        etudiant=None,
        document=None,
        details: dict | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        if favori is not None:
            etudiant = etudiant or getattr(favori, "etudiant", None)
            document = document or getattr(favori, "document", None)

        mapping = {
            "AJOUT": cls.ACTIONS.FAVORI_AJOUT,
            "SUPPRESSION": cls.ACTIONS.FAVORI_SUPPRESSION,
        }
        payload = {
            "favori_id": str(getattr(favori, "id", "")) or None,
            "etudiant_id": str(getattr(etudiant, "id", "")) or None,
            "etudiant_email": getattr(getattr(etudiant, "user", None), "email", None),
            "document_id": str(getattr(document, "id", "")) or None,
            "document_titre": getattr(document, "title", None),
        }
        if details:
            payload.update(details)
        return cls.log(
            action=mapping.get(action_type, cls.ACTIONS.FAVORI_AJOUT),
            user=user,
            ip_address=ip,
            user_agent=ua,
            details=payload,
        )

    @classmethod
    def log_consultation(
        cls,
        action_type: str,
        user,
        consultation=None,
        document=None,
        recherche_query: str | None = None,
        details: dict | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str | None:
        if consultation is not None:
            document = document or getattr(consultation, "document", None)
            recherche_query = recherche_query or getattr(consultation, "recherche_query", None)

        mapping = {
            "VUE": cls.ACTIONS.CONSULTATION_VUE,
            "RECHERCHE": cls.ACTIONS.CONSULTATION_RECHERCHE,
            "TERMINEE": cls.ACTIONS.CONSULTATION_TERMINEE,
        }
        payload = {
            "consultation_id": str(getattr(consultation, "id", "")) or None,
            "type_consultation": getattr(consultation, "type_consultation", None),
            "document_id": str(getattr(document, "id", "")) or None,
            "document_titre": getattr(document, "title", None),
            "recherche_query": recherche_query,
            "duree_secondes": getattr(consultation, "duree_secondes", None),
        }
        if details:
            payload.update(details)
        return cls.log(
            action=mapping.get(action_type, cls.ACTIONS.CONSULTATION_VUE),
            user=user,
            ip_address=ip,
            user_agent=ua,
            details=payload,
        )

    @classmethod
    def _base_queryset(cls):
        return HistoriqueAction.objects.select_related("user").order_by("-created_at")

    @classmethod
    def get_historique_user(cls, user_id: str, limit: int = 50) -> list[dict]:
        queryset = cls._base_queryset().filter(user_id=user_id)[:limit]
        return [cls._serialize(log) for log in queryset]

    @classmethod
    def get_historique_action(cls, action: str, limit: int = 100) -> list[dict]:
        queryset = cls._base_queryset().filter(action=action)[:limit]
        return [cls._serialize(log) for log in queryset]

    @classmethod
    def get_echecs_recents(cls, minutes: int = 30) -> list[dict]:
        since = timezone.now() - timedelta(minutes=minutes)
        queryset = cls._base_queryset().filter(
            statut=cls.STATUTS.ECHEC,
            created_at__gte=since,
        )
        return [cls._serialize(log) for log in queryset]

    @classmethod
    def get_stats(cls, days: int = 30) -> list[dict]:
        since = timezone.now() - timedelta(days=days)
        stats = (
            HistoriqueAction.objects.filter(created_at__gte=since)
            .values("action")
            .annotate(
                total=models.Count("id"),
                echecs=models.Count(
                    "id",
                    filter=models.Q(statut=cls.STATUTS.ECHEC),
                ),
            )
            .order_by("-total", "action")
        )
        return [
            {
                "action": item["action"],
                "action_label": cls.get_action_label(item["action"]),
                "total": item["total"],
                "echecs": item["echecs"],
            }
            for item in stats
        ]

    @classmethod
    def _serialize(cls, log: HistoriqueAction) -> dict:
        return {
            "id": str(log.pk),
            "action": log.action,
            "action_label": cls.get_action_label(log.action),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": log.user_email,
            "user_type": log.user_type,
            "details": log.details or {},
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "statut": log.statut,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
