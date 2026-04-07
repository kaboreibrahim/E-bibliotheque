"""
=============================================================================
 mongo_client.py — Connexion singleton PyMongo
 Emplacement recommandé : bibliotheque/config/mongo_client.py
=============================================================================

 Usage dans n'importe quel fichier Django :

    from config.mongo_client import get_db, get_collection

    db  = get_db()
    col = get_collection('historique_actions')
    col.insert_one({...})

=============================================================================
"""

import logging
from threading import Lock

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── Singleton thread-safe ────────────────────────────────────────────────────
_client: MongoClient | None = None
_lock   = Lock()


def _build_uri() -> str:
    """Construit l'URI de connexion MongoDB depuis settings.MONGODB."""
    cfg  = getattr(settings, 'MONGODB', {})
    uri  = cfg.get('URI') or getattr(settings, 'MONGO_URL', '')
    if uri:
        return uri

    user = cfg.get('USER', '')
    pwd  = cfg.get('PASSWORD', '')
    host = cfg.get('HOST', 'localhost')
    port = cfg.get('PORT', 27017)
    auth = cfg.get('AUTH_SOURCE', 'admin')

    if user and pwd:
        return f"mongodb://{user}:{pwd}@{host}:{port}/?authSource={auth}"
    return f"mongodb://{host}:{port}/"


def get_client() -> MongoClient:
    """Retourne le client PyMongo (singleton)."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:   # double-check inside lock
                try:
                    uri    = _build_uri()
                    # Configuration SSL pour MongoDB Atlas
                    if "mongodb+srv://" in uri:
                        _client = MongoClient(
                            uri,
                            serverSelectionTimeoutMS=10000,  # Increased timeout
                            connectTimeoutMS=10000,          # Increased timeout
                            socketTimeoutMS=20000,          # Increased timeout
                            maxPoolSize=50,
                            retryWrites=True,
                            tls=True,
                            tlsAllowInvalidCertificates=False,
                            tlsAllowInvalidHostnames=False,
                            retryReads=True,
                            ssl_cert_reqs=None,  # More permissive SSL
                        )
                    else:
                        # Configuration pour MongoDB local
                        _client = MongoClient(
                            uri,
                            serverSelectionTimeoutMS=5000,
                            connectTimeoutMS=5000,
                            socketTimeoutMS=10000,
                            maxPoolSize=50,
                            retryWrites=True,
                        )
                    # Ping pour valider la connexion
                    _client.admin.command('ping')
                    logger.info("✅ Connexion MongoDB établie.")
                    _ensure_indexes(_client)
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    logger.error(f"❌ MongoDB indisponible : {e}")
                    raise
    return _client


def get_db():
    """Retourne la base MongoDB configurée."""
    return get_client()[settings.MONGODB['DB']]


def get_collection(name: str):
    """Retourne une collection par son nom logique (clé COLLECTIONS ou nom direct)."""
    col_name = settings.MONGODB['COLLECTIONS'].get(name, name)
    return get_db()[col_name]


# ─── Index automatiques ───────────────────────────────────────────────────────

def _ensure_indexes(client: MongoClient):
    """
    Crée les index MongoDB au démarrage.
    Idempotent — sans effet si les index existent déjà.
    """
    db  = client[settings.MONGODB['DB']]
    ttl = settings.MONGODB.get('TTL_SECONDS', 15_552_000)  # 180 jours par défaut

    # ── Collection : historique_actions ──────────────────────────────────────
    hist = db['historique_actions']

    # TTL index — suppression automatique des vieux logs
    hist.create_index(
        [('created_at', ASCENDING)],
        expireAfterSeconds=ttl,
        name='idx_ttl_created_at'
    )
    # Recherche par utilisateur
    hist.create_index([('user_id',   ASCENDING)], name='idx_user_id')
    # Recherche par type d'action
    hist.create_index([('action',    ASCENDING)], name='idx_action')
    # Tri chronologique rapide
    hist.create_index([('created_at', DESCENDING)], name='idx_created_at_desc')
    # Index composé : utilisateur + action (filtres fréquents dans l'admin)
    hist.create_index(
        [('user_id', ASCENDING), ('action', ASCENDING), ('created_at', DESCENDING)],
        name='idx_user_action_date'
    )

    logger.info("✅ Index MongoDB créés / vérifiés.")
