"""
=============================================================================
 apps/users/services/notification_service.py
 COUCHE SERVICE — Emails envoyés à la création d'un compte
=============================================================================
"""

import logging
from email.message import MIMEPart
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.users.models.user_models import User

logger = logging.getLogger(__name__)

# Logo joint au message (et non lié) : il s'affiche même quand la messagerie
# bloque les images distantes.
LOGO_PATH = Path(__file__).resolve().parent.parent / 'static' / 'emails' / 'logo-ufr-sjap.jpg'
LOGO_CID = 'logo-ufr-sjap'


def _logo_inline() -> MIMEPart | None:
    """Logo à insérer dans l'email, ou None si le fichier n'a pas été déployé."""
    try:
        data = LOGO_PATH.read_bytes()
    except OSError as e:
        logger.warning(f"Logo des emails illisible: {e}")
        return None
    logo = MIMEPart()
    logo.set_content(
        data, maintype='image', subtype='jpeg',
        disposition='inline', filename=LOGO_PATH.name, cid=f'<{LOGO_CID}>',
    )
    return logo


def envoyer_identifiants(
    user: User,
    mot_de_passe: str,
    matricule: str = None,
    validite: str = '',
) -> bool:
    """
    Envoie au titulaire ses identifiants (matricule pour un étudiant, adresse
    email pour les autres comptes), le mot de passe temporaire et la marche à
    suivre pour la première connexion.

    Un échec d'envoi n'annule pas la création du compte : il est journalisé et
    signalé par le retour False. Le mot de passe n'est jamais écrit dans les logs.
    """
    logo = _logo_inline()
    context = {
        'user_name':         user.get_full_name() or user.email,
        'type_compte':       user.get_user_type_display(),
        'identifiant_label': 'Matricule' if matricule else 'Adresse email',
        'identifiant_nom':   'matricule' if matricule else 'adresse email',
        'identifiant':       matricule or user.email,
        'mot_de_passe':      mot_de_passe,
        'validite':          validite,
        'site_url':          settings.FRONTEND_URL,
        'login_url':         f'{settings.FRONTEND_URL}/auth/login/',
        'site_nom':          urlsplit(settings.FRONTEND_URL).netloc,
        'logo_cid':          LOGO_CID if logo else '',
        'annee':             timezone.localdate().year,
    }
    try:
        msg = EmailMultiAlternatives(
            subject='Vos identifiants de connexion — PERED',
            body=render_to_string('emails/identifiants.txt', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(render_to_string('emails/identifiants.html', context), 'text/html')
        if logo:
            msg.attach(logo)
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Erreur envoi des identifiants à {user.email}: {e}")
        return False
