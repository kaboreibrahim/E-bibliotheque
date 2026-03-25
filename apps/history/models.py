import uuid
import logging
from datetime import datetime, timezone as dt_tz
 
from django.db import models
from django.utils import timezone
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
 
# Importer User et Document depuis leurs apps respectives
# from apps.users.models import User
# from apps.documents.models import Document
 
logger = logging.getLogger(__name__)
# =============================================================================
# 📋  HISTORIQUE ACTION — Service MongoDB (PyMongo)
# =============================================================================
 
class HistoriqueActionService:
    """
    Service statique pour enregistrer toutes les actions dans MongoDB.
 
    Chaque document MongoDB a la structure suivante :
    {
        "_id"        : ObjectId (auto),
        "action"     : str,          # code de l'action (voir ACTIONS)
        "user_id"    : str,          # UUID de l'utilisateur
        "user_email" : str,
        "user_type"  : str,          # ETUDIANT / BIBLIOTHECAIRE / ADMINISTRATEUR
        "details"    : dict,         # données spécifiques à l'action
        "ip_address" : str | None,
        "user_agent" : str | None,
        "created_at" : datetime (UTC),
        "statut"     : str,          # "succes" | "echec"
    }
    """
 
    # ── Catalogue des actions ─────────────────────────────────────────────────
    class ACTIONS:
        # Auth
        CONNEXION              = 'CONNEXION'
        DECONNEXION            = 'DECONNEXION'
        CONNEXION_ECHEC        = 'CONNEXION_ECHEC'
 
        # 2FA / OTP
        OTP_ECHEC              = 'OTP_ECHEC'
        TOTP_ACTIVE            = 'TOTP_ACTIVE'
        TOTP_ECHEC             = 'TOTP_ECHEC'
 
        # Documents
        DOCUMENT_AJOUT         = 'DOCUMENT_AJOUT'
        DOCUMENT_MODIFICATION  = 'DOCUMENT_MODIFICATION'
        DOCUMENT_SUPPRESSION   = 'DOCUMENT_SUPPRESSION'
 
        # Utilisateurs
        UTILISATEUR_CREATION   = 'UTILISATEUR_CREATION'
        UTILISATEUR_MODIF      = 'UTILISATEUR_MODIF'
        UTILISATEUR_DESACTIVE  = 'UTILISATEUR_DESACTIVE'
        UTILISATEUR_SUPPRIME   = 'UTILISATEUR_SUPPRIME'
 
    @staticmethod
    def _get_collection():
        """Récupère la collection MongoDB (import tardif pour éviter les cycles)."""
        from core.mongo_client import get_collection
        return get_collection('historique_actions')
 
    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        details: dict = None,
        statut: str = 'succes',
        ip_address: str = None,
        user_agent: str = None,
    ) -> str | None:
        """
        Enregistre une action dans MongoDB.
 
        Paramètres :
            action      : code action (utiliser HistoriqueActionService.ACTIONS.XXX)
            user        : instance User Django (optionnel pour les actions anonymes)
            details     : dict de données supplémentaires libres
            statut      : 'succes' ou 'echec'
            ip_address  : adresse IP du client
            user_agent  : user-agent du navigateur
 
        Retourne l'_id MongoDB inséré (str) ou None en cas d'erreur.
        """
        document = {
            "action":      action,
            "user_id":     str(user.id)        if user else None,
            "user_email":  user.email          if user else None,
            "user_type":   user.user_type      if user else None,
            "details":     details or {},
            "ip_address":  ip_address,
            "user_agent":  user_agent,
            "statut":      statut,
            "created_at":  datetime.now(dt_tz.utc),
        }
        try:
            col    = cls._get_collection()
            result = col.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            # Ne jamais bloquer l'app si MongoDB est indisponible
            logger.error(f"[MongoDB] Erreur lors du log '{action}' : {e}")
            return None
 
    # ── Méthodes raccourcis ───────────────────────────────────────────────────
 
    @classmethod
    def log_connexion(cls, user, statut='succes', ip=None, ua=None):
        return cls.log(
            action=cls.ACTIONS.CONNEXION if statut == 'succes' else cls.ACTIONS.CONNEXION_ECHEC,
            user=user, statut=statut, ip_address=ip, user_agent=ua,
            details={"email": user.email if user else None}
        )
 
    @classmethod
    def log_deconnexion(cls, user, ip=None, ua=None):
        return cls.log(
            action=cls.ACTIONS.DECONNEXION,
            user=user, ip_address=ip, user_agent=ua
        )
 
    @classmethod
    def log_otp_echec(cls, user, type_otp='email', ip=None, ua=None):
        return cls.log(
            action=cls.ACTIONS.OTP_ECHEC,
            user=user, statut='echec', ip_address=ip, user_agent=ua,
            details={"type_otp": type_otp, "tentatives": user.codes_verification
                     .filter(is_used=False).first().attempts if user else None}
        )
 
    @classmethod
    def log_totp(cls, user, statut='succes', ip=None, ua=None):
        action = cls.ACTIONS.TOTP_ACTIVE if statut == 'succes' else cls.ACTIONS.TOTP_ECHEC
        return cls.log(action=action, user=user, statut=statut, ip_address=ip, user_agent=ua)
 
    @classmethod
    def log_document(cls, action_type, user, document, details: dict = None, ip=None, ua=None):
        """
        action_type : 'AJOUT' | 'MODIFICATION' | 'SUPPRESSION'
        """
        mapping = {
            'AJOUT':        cls.ACTIONS.DOCUMENT_AJOUT,
            'MODIFICATION': cls.ACTIONS.DOCUMENT_MODIFICATION,
            'SUPPRESSION':  cls.ACTIONS.DOCUMENT_SUPPRESSION,
        }
        return cls.log(
            action=mapping.get(action_type, 'DOCUMENT_ACTION'),
            user=user, ip_address=ip, user_agent=ua,
            details={
                "document_id":    str(document.id),
                "document_titre": document.title,
                "document_type":  document.type,
                **(details or {})
            }
        )
 
    @classmethod
    def log_utilisateur(cls, action_type, auteur, cible_user, details: dict = None, ip=None, ua=None):
        """
        action_type : 'CREATION' | 'MODIF' | 'DESACTIVE' | 'SUPPRIME'
        auteur      : utilisateur qui effectue l'action (admin/biblio)
        cible_user  : utilisateur concerné par l'action
        """
        mapping = {
            'CREATION':  cls.ACTIONS.UTILISATEUR_CREATION,
            'MODIF':     cls.ACTIONS.UTILISATEUR_MODIF,
            'DESACTIVE': cls.ACTIONS.UTILISATEUR_DESACTIVE,
            'SUPPRIME':  cls.ACTIONS.UTILISATEUR_SUPPRIME,
        }
        return cls.log(
            action=mapping.get(action_type, 'UTILISATEUR_ACTION'),
            user=auteur, ip_address=ip, user_agent=ua,
            details={
                "cible_id":       str(cible_user.id),
                "cible_email":    cible_user.email,
                "cible_type":     cible_user.user_type,
                **(details or {})
            }
        )
 
    # ── Requêtes / Lecture ────────────────────────────────────────────────────
 
    @classmethod
    def get_historique_user(cls, user_id: str, limit: int = 50) -> list:
        """Récupère les N dernières actions d'un utilisateur."""
        try:
            col  = cls._get_collection()
            docs = col.find(
                {"user_id": str(user_id)},
                sort=[("created_at", -1)],
                limit=limit
            )
            return [cls._serialize(d) for d in docs]
        except Exception as e:
            logger.error(f"[MongoDB] get_historique_user : {e}")
            return []
 
    @classmethod
    def get_historique_action(cls, action: str, limit: int = 100) -> list:
        """Récupère les N dernières occurrences d'un type d'action."""
        try:
            col  = cls._get_collection()
            docs = col.find(
                {"action": action},
                sort=[("created_at", -1)],
                limit=limit
            )
            return [cls._serialize(d) for d in docs]
        except Exception as e:
            logger.error(f"[MongoDB] get_historique_action : {e}")
            return []
 
    @classmethod
    def get_echecs_recents(cls, minutes: int = 30) -> list:
        """Retourne les actions en échec des N dernières minutes (alertes sécurité)."""
        from datetime import timedelta
        depuis = datetime.now(dt_tz.utc) - timedelta(minutes=minutes)
        try:
            col  = cls._get_collection()
            docs = col.find(
                {"statut": "echec", "created_at": {"$gte": depuis}},
                sort=[("created_at", -1)]
            )
            return [cls._serialize(d) for d in docs]
        except Exception as e:
            logger.error(f"[MongoDB] get_echecs_recents : {e}")
            return []
 
    @staticmethod
    def _serialize(doc: dict) -> dict:
        """Convertit un document MongoDB en dict JSON-compatible."""
        doc['_id'] = str(doc['_id'])
        if isinstance(doc.get('created_at'), datetime):
            doc['created_at'] = doc['created_at'].isoformat()
        return doc
 
