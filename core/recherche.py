"""
Recherche globale de l'administration : GET /api/recherche/?q=<texte>&limite=5

Une seule requete renvoie, groupes par nature, les meilleurs resultats parmi :
documents, etudiants, autres comptes (bibliothecaires, enseignants-chercheurs,
chercheurs, personnes externes), UE / ECUE, specialites et filieres.
Chaque groupe porte aussi son nombre total de correspondances.

Reserve aux administrateurs et bibliothecaires (ce sont eux qui voient la
barre de recherche de l'administration).
"""
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.filiere.models import Filiere
from apps.specialites.models import Specialite
from apps.ue.models import ECUE, UE
from apps.users.models import Etudiant, User
from apps.users.permissions import IsAdminOrBibliothecaire

LONGUEUR_MIN = 2
LIMITE_DEFAUT = 5
LIMITE_MAX = 20

TYPES_PERSONNEL = (
    User.UserType.BIBLIOTHECAIRE,
    User.UserType.ENSEIGNANT_CHERCHEUR,
    User.UserType.CHERCHEUR,
    User.UserType.PERSONNE_EXTERNE,
)


def _nom(user) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _groupe(cle, libelle, queryset, limite, formatter):
    total = queryset.count()
    return {
        "type": cle,
        "libelle": libelle,
        "total": total,
        "resultats": [formatter(obj) for obj in queryset[:limite]] if total else [],
    }


def rechercher(q: str, limite: int = LIMITE_DEFAUT) -> dict:
    q = (q or "").strip()
    if len(q) < LONGUEUR_MIN:
        return {"query": q, "total": 0, "groupes": []}

    documents = (
        Document.objects.select_related("type", "niveau", "ue")
        .filter(
            # memes champs que la recherche de la page Documents (lien « voir tout »)
            Q(title__icontains=q)
            | Q(auteur__icontains=q)
            | Q(description__icontains=q)
            | Q(specialite__name__icontains=q)
            | Q(ue__code__icontains=q)
            | Q(ue__name__icontains=q)
        )
        .order_by("-created_at")
    )
    etudiants = (
        Etudiant.objects.select_related("user", "niveau", "specialite")
        .filter(
            Q(matricule__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__phone__icontains=q)
        )
        .order_by("user__last_name", "user__first_name")
    )
    personnel = (
        User.objects.filter(user_type__in=TYPES_PERSONNEL)
        .filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )
        .order_by("last_name", "first_name")
    )
    ues = UE.objects.filter(Q(code__icontains=q) | Q(name__icontains=q)).order_by("code")
    ecues = ECUE.objects.select_related("ue").filter(Q(code__icontains=q) | Q(name__icontains=q)).order_by("code")
    specialites = Specialite.objects.select_related("niveau").filter(name__icontains=q).order_by("name")
    filieres = Filiere.objects.filter(name__icontains=q).order_by("name")
    libelles_types = dict(User.UserType.choices)

    groupes = [
        _groupe("documents", "Documents", documents, limite, lambda d: {
            "id": str(d.pk),
            "titre": d.title,
            "sous_titre": " · ".join(filter(None, [
                d.type.name if d.type_id else None,
                d.niveau.name if d.niveau_id else None,
                d.ue.code if d.ue_id else None,
                d.auteur,
            ])),
        }),
        _groupe("etudiants", "Étudiants", etudiants, limite, lambda e: {
            "id": str(e.pk),
            "titre": _nom(e.user),
            "sous_titre": " · ".join(filter(None, [
                e.matricule,
                e.niveau.name if e.niveau_id else None,
                e.specialite.name if e.specialite_id else None,
            ])),
            "matricule": e.matricule,
            "email": e.user.email,
        }),
        _groupe("personnel", "Personnel et lecteurs externes", personnel, limite, lambda u: {
            "id": str(u.pk),
            "titre": _nom(u),
            "sous_titre": f"{libelles_types.get(u.user_type, u.user_type)} · {u.email}",
            "user_type": u.user_type,
            "email": u.email,
        }),
        _groupe("ues", "Unités d'enseignement", ues, limite, lambda u: {
            "id": str(u.pk),
            "titre": f"{u.code} — {u.name}",
            "sous_titre": "UE",
            "code": u.code,
        }),
        _groupe("ecues", "ECUE", ecues, limite, lambda e: {
            "id": str(e.pk),
            "titre": f"{e.code} — {e.name}",
            "sous_titre": f"ECUE de l'UE {e.ue.code}" if e.ue_id else "ECUE",
            "code": e.code,
        }),
        _groupe("specialites", "Spécialités", specialites, limite, lambda s: {
            "id": str(s.pk),
            "titre": s.name,
            "sous_titre": s.niveau.name if s.niveau_id else "Spécialité",
        }),
        _groupe("filieres", "Filières", filieres, limite, lambda f: {
            "id": str(f.pk),
            "titre": f.name,
            "sous_titre": "Filière",
        }),
    ]
    groupes = [g for g in groupes if g["total"]]
    return {"query": q, "total": sum(g["total"] for g in groupes), "groupes": groupes}


class RechercheGlobaleView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrBibliothecaire]

    @extend_schema(
        summary="Recherche globale de l'administration",
        tags=["Recherche"],
        description=(
            "Cherche le texte `q` (2 caracteres minimum) dans les documents, les comptes, "
            "les UE / ECUE, les specialites et les filieres. Resultats groupes par nature, "
            "`limite` par groupe (defaut 5, max 20), avec le total de chaque groupe."
        ),
        parameters=[
            OpenApiParameter(name="q", description="Texte recherche (2 caracteres minimum)", required=True, type=str),
            OpenApiParameter(name="limite", description="Resultats par groupe (1 a 20, defaut 5)", required=False, type=int),
        ],
        responses={200: OpenApiResponse(description="Resultats groupes.")},
    )
    def get(self, request):
        try:
            limite = int(request.query_params.get("limite", LIMITE_DEFAUT))
        except (TypeError, ValueError):
            limite = LIMITE_DEFAUT
        limite = max(1, min(LIMITE_MAX, limite))
        return Response(rechercher(request.query_params.get("q", ""), limite))
