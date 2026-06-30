"""Regles metier partagees autour des specialites."""

NIVEAUX_AVEC_SPECIALITE = ("L1", "L2", "L3", "M1", "M2", "DOCTORAT")
NIVEAUX_TRONC_COMMUN = ()

LIBELLE_NIVEAUX_AVEC_SPECIALITE = ", ".join(NIVEAUX_AVEC_SPECIALITE)
LIBELLE_NIVEAUX_TRONC_COMMUN = ", ".join(NIVEAUX_TRONC_COMMUN)


def niveau_accepte_specialite(niveau_name: str | None) -> bool:
    return niveau_name in NIVEAUX_AVEC_SPECIALITE


def niveau_est_tronc_commun(niveau_name: str | None) -> bool:
    return niveau_name in NIVEAUX_TRONC_COMMUN
