"""
=============================================================================
 middleware.py — Extraction automatique IP + User-Agent
 Emplacement : apps/consultations/middleware.py
=============================================================================

 Ajoutez dans settings.py → MIDDLEWARE :
   'apps.consultations.middleware.RequestMetaMiddleware'

 Ensuite dans n'importe quelle vue DRF :
   ip = request.META.get('CLIENT_IP')
   ua = request.META.get('CLIENT_UA')

=============================================================================
"""


class RequestMetaMiddleware:
    """
    Injecte l'IP réelle et le User-Agent dans request.META
    pour qu'ils soient accessibles partout sans duplication de code.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META['CLIENT_IP'] = self._get_ip(request)
        request.META['CLIENT_UA'] = request.META.get('HTTP_USER_AGENT', '')
        return self.get_response(request)

    @staticmethod
    def _get_ip(request) -> str | None:
        """
        Récupère la vraie IP derrière un proxy/load balancer.
        Ordre de priorité :
          1. X-Forwarded-For (proxy)
          2. X-Real-IP (nginx)
          3. REMOTE_ADDR (fallback)
        """
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # X-Forwarded-For peut contenir plusieurs IP : "client, proxy1, proxy2"
            return xff.split(',')[0].strip()

        x_real = request.META.get('HTTP_X_REAL_IP')
        if x_real:
            return x_real.strip()

        return request.META.get('REMOTE_ADDR')


# =============================================================================
# 📌  HELPER — à utiliser dans les vues DRF
# =============================================================================

def get_request_meta(request) -> dict:
    """
    Retourne un dict {ip_address, user_agent} prêt à passer au service de log.

    Exemple dans une vue :
        from apps.consultations.middleware import get_request_meta
        from apps.history.models import HistoriqueActionService

        meta = get_request_meta(request)
        HistoriqueActionService.log_connexion(user=user, **meta)
    """
    return {
        'ip':  request.META.get('CLIENT_IP'),
        'ua':  request.META.get('CLIENT_UA', ''),
    }
