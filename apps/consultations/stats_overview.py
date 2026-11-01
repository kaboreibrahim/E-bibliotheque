"""
Agregats du tableau de bord d'administration (courbes et diagrammes).

Toutes les series sont calculees en base (une requete groupee par serie) et
completees cote Python pour que les jours / mois sans activite valent 0.
Les consultations supprimees par les lecteurs de leur historique restent
comptees : la suppression est logique (safedelete) et ne doit pas fausser
les statistiques de frequentation.
"""
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate, TruncMonth
from django.utils import timezone

from apps.consultations.models import Consultation
from apps.documents.models.document import Document

PERIODES_AUTORISEES = (7, 30, 90, 365)
MOIS_FR = ["janv.", "fevr.", "mars", "avr.", "mai", "juin", "juil.", "aout", "sept.", "oct.", "nov.", "dec."]


def _debut_du_jour(jour: date) -> datetime:
    return timezone.make_aware(datetime.combine(jour, time.min), timezone.get_current_timezone())


def _variation(courant: int, precedent: int):
    """Variation en % par rapport a la periode precedente (None si pas de base)."""
    if not precedent:
        return None
    return round((courant - precedent) * 100 / precedent, 1)


def _mois_precedents(nb: int, aujourdhui: date) -> list[date]:
    mois = []
    annee, m = aujourdhui.year, aujourdhui.month
    for _ in range(nb):
        mois.append(date(annee, m, 1))
        m -= 1
        if m == 0:
            annee, m = annee - 1, 12
    return list(reversed(mois))


def _cle_jour(valeur) -> date:
    return valeur.date() if isinstance(valeur, datetime) else valeur


def build_overview(jours: int = 30) -> dict:
    if jours not in PERIODES_AUTORISEES:
        jours = 30
    aujourdhui = timezone.localdate()
    debut = aujourdhui - timedelta(days=jours - 1)
    debut_dt = _debut_du_jour(debut)
    fin_dt = _debut_du_jour(aujourdhui + timedelta(days=1))
    prec_debut_dt = _debut_du_jour(debut - timedelta(days=jours))

    toutes = Consultation.all_objects.all()
    periode = toutes.filter(debut_consultation__gte=debut_dt, debut_consultation__lt=fin_dt)
    precedente = toutes.filter(debut_consultation__gte=prec_debut_dt, debut_consultation__lt=debut_dt)

    # ── Indicateurs cles ────────────────────────────────────────────────────
    def _kpis(qs):
        return qs.aggregate(
            lectures=Count("id", filter=Q(type_consultation="VUE")),
            recherches=Count("id", filter=Q(type_consultation="RECHERCHE")),
            lecteurs=Count("user", distinct=True),
            duree=Avg("duree_secondes", filter=Q(type_consultation="VUE", duree_secondes__gt=0)),
        )

    k, kp = _kpis(periode), _kpis(precedente)
    kpis = {
        "lectures": k["lectures"],
        "lectures_variation": _variation(k["lectures"], kp["lectures"]),
        "recherches": k["recherches"],
        "recherches_variation": _variation(k["recherches"], kp["recherches"]),
        "lecteurs_actifs": k["lecteurs"],
        "lecteurs_actifs_variation": _variation(k["lecteurs"], kp["lecteurs"]),
        "duree_moyenne_secondes": int(k["duree"] or 0),
        "nouveaux_documents": Document.objects.filter(created_at__gte=debut_dt, created_at__lt=fin_dt).count(),
    }

    # ── Activite quotidienne ────────────────────────────────────────────────
    par_jour = {
        _cle_jour(row["jour"]): row
        for row in periode.annotate(jour=TruncDate("debut_consultation"))
        .values("jour")
        .annotate(
            lectures=Count("id", filter=Q(type_consultation="VUE")),
            recherches=Count("id", filter=Q(type_consultation="RECHERCHE")),
            lecteurs=Count("user", distinct=True),
        )
    }
    activite = []
    for i in range(jours):
        jour = debut + timedelta(days=i)
        row = par_jour.get(jour, {})
        activite.append({
            "date": jour.isoformat(),
            "lectures": row.get("lectures", 0),
            "recherches": row.get("recherches", 0),
            "lecteurs": row.get("lecteurs", 0),
        })

    # ── Repartition horaire des lectures ────────────────────────────────────
    par_heure = {
        row["heure"]: row["nb"]
        for row in periode.filter(type_consultation="VUE")
        .annotate(heure=ExtractHour("debut_consultation"))
        .values("heure")
        .annotate(nb=Count("id"))
    }
    heures = [{"heure": h, "lectures": par_heure.get(h, 0)} for h in range(24)]

    # ── Croissance du fonds documentaire (12 derniers mois) ─────────────────
    mois = _mois_precedents(12, aujourdhui)
    debut_mois_dt = _debut_du_jour(mois[0])
    ajouts = {
        _cle_jour(row["mois"]).replace(day=1): row["nb"]
        for row in Document.objects.filter(created_at__gte=debut_mois_dt)
        .annotate(mois=TruncMonth("created_at"))
        .values("mois")
        .annotate(nb=Count("id"))
    }
    cumul = Document.objects.filter(created_at__lt=debut_mois_dt).count()
    documents_par_mois = []
    for m in mois:
        nb = ajouts.get(m, 0)
        cumul += nb
        documents_par_mois.append({"mois": m.isoformat()[:7], "libelle": f"{MOIS_FR[m.month - 1]} {str(m.year)[2:]}", "ajouts": nb, "total": cumul})

    # ── Repartitions du fonds ───────────────────────────────────────────────
    par_type = [
        {"code": r["type__code"], "libelle": r["type__name"], "nb": r["nb"]}
        for r in Document.objects.values("type__code", "type__name").annotate(nb=Count("id")).order_by("-nb")
    ]
    par_niveau = [
        {"libelle": r["niveau__name"] or "Sans niveau", "nb": r["nb"]}
        for r in Document.objects.values("niveau__name").annotate(nb=Count("id")).order_by("niveau__name")
    ]

    # ── Comptes utilisateurs ────────────────────────────────────────────────
    User = get_user_model()
    libelles = dict(User.UserType.choices)
    utilisateurs = [
        {
            "type": r["user_type"],
            "libelle": libelles.get(r["user_type"], r["user_type"]),
            "total": r["total"],
            "actifs": r["actifs"],
        }
        for r in User.objects.values("user_type")
        .annotate(total=Count("id"), actifs=Count("id", filter=Q(is_active=True)))
        .order_by("-total")
    ]

    return {
        "periode": {"jours": jours, "debut": debut.isoformat(), "fin": aujourdhui.isoformat()},
        "kpis": kpis,
        "activite_quotidienne": activite,
        "activite_horaire": heures,
        "documents_par_mois": documents_par_mois,
        "documents_par_type": par_type,
        "documents_par_niveau": par_niveau,
        "utilisateurs_par_type": utilisateurs,
    }


# =============================================================================
# Statistiques personnelles du lecteur connecte (tableau de bord etudiant)
# =============================================================================

PERIODES_PERSONNELLES = (7, 30, 90)


def build_personal(user, jours: int = 30) -> dict:
    """
    Activite de lecture du lecteur connecte. Les entrees qu'il a effacees de son
    historique ne sont pas comptees (c'est son espace personnel).
    """
    if jours not in PERIODES_PERSONNELLES:
        jours = 30
    aujourdhui = timezone.localdate()
    debut = aujourdhui - timedelta(days=jours - 1)
    debut_dt = _debut_du_jour(debut)
    fin_dt = _debut_du_jour(aujourdhui + timedelta(days=1))
    prec_debut_dt = _debut_du_jour(debut - timedelta(days=jours))

    mes = Consultation.objects.filter(user=user)
    lectures = mes.filter(type_consultation="VUE")
    periode = mes.filter(debut_consultation__gte=debut_dt, debut_consultation__lt=fin_dt)
    lectures_periode = lectures.filter(debut_consultation__gte=debut_dt, debut_consultation__lt=fin_dt)
    lectures_prec = lectures.filter(debut_consultation__gte=prec_debut_dt, debut_consultation__lt=debut_dt).count()

    k = periode.aggregate(
        lectures=Count("id", filter=Q(type_consultation="VUE")),
        recherches=Count("id", filter=Q(type_consultation="RECHERCHE")),
        documents=Count("document", filter=Q(type_consultation="VUE"), distinct=True),
        temps=Sum("duree_secondes", filter=Q(type_consultation="VUE")),
    )

    # Lectures et minutes par jour
    par_jour = {
        _cle_jour(r["jour"]): r
        for r in lectures_periode.annotate(jour=TruncDate("debut_consultation"))
        .values("jour")
        .annotate(nb=Count("id"), secondes=Sum("duree_secondes"))
    }
    activite = []
    for i in range(jours):
        jour = debut + timedelta(days=i)
        r = par_jour.get(jour, {})
        activite.append({"date": jour.isoformat(), "lectures": r.get("nb", 0), "minutes": round((r.get("secondes") or 0) / 60)})

    # Serie : jours consecutifs avec au moins une lecture, jusqu'a aujourd'hui (ou hier)
    jours_lus = set(
        _cle_jour(d)
        for d in lectures.filter(debut_consultation__gte=_debut_du_jour(aujourdhui - timedelta(days=365)))
        .annotate(jour=TruncDate("debut_consultation"))
        .values_list("jour", flat=True)
    )
    serie = 0
    jour = aujourdhui if aujourdhui in jours_lus else aujourdhui - timedelta(days=1)
    while jour in jours_lus:
        serie += 1
        jour -= timedelta(days=1)

    par_type = [
        {"code": r["document__type__code"], "libelle": r["document__type__name"], "nb": r["nb"]}
        for r in lectures_periode.filter(document__isnull=False)
        .values("document__type__code", "document__type__name")
        .annotate(nb=Count("id"))
        .order_by("-nb")
    ]
    # Matieres : l'ECUE du document, regroupee par UE parente
    par_ue = [
        {"code": r["document__ue__ue__code"], "libelle": r["document__ue__ue__name"], "nb": r["nb"]}
        for r in lectures_periode.filter(document__ue__isnull=False)
        .values("document__ue__ue__code", "document__ue__ue__name")
        .annotate(nb=Count("id"))
        .order_by("-nb")[:5]
    ]

    return {
        "periode": {"jours": jours, "debut": debut.isoformat(), "fin": aujourdhui.isoformat()},
        "kpis": {
            "lectures": k["lectures"],
            "lectures_variation": _variation(k["lectures"], lectures_prec),
            "documents_distincts": k["documents"],
            "temps_lecture_secondes": int(k["temps"] or 0),
            "recherches": k["recherches"],
            "jours_actifs": sum(1 for j in activite if j["lectures"]),
            "serie_jours": serie,
        },
        "activite_quotidienne": activite,
        "lectures_par_type": par_type,
        "lectures_par_ue": par_ue,
    }
