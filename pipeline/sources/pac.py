"""Source : bénéficiaires des aides de la PAC (FEAGA/FEADER), publiés par l'ASP.

Cadre : règlement (UE) 2021/2116, publication annuelle par exercice financier
(16/10/N-1 -> 15/10/N), rétention 2 ans. Il n'existe PAS de jeu exploitable sur
data.gouv.fr (vérifié 2026-07 : l'organisation ASP n'y publie que des archives
2005-2013). La vraie source est le portail de reporting de l'ASP, lié depuis
https://agriculture.gouv.fr/les-beneficiaires-des-aides-de-la-pac

Accès programmatique validé sur données réelles (2026-07) : API REST
MicroStrategy du portail, session anonyme (loginMode 8, sans credentials),
lecture paginée du cube « Paiements EF <année> agrégés public ».
Grain : bénéficiaire x mesure ; ~1,3 M lignes pour l'EF 2025.

ROTATION ANNUELLE : les identifiants d'application/projet/cube changent à
chaque exercice publié (au printemps). Mettre à jour CUBE_ID/PROJECT_ID depuis
la page agriculture.gouv.fr ci-dessus. Fail-loud si le cube ne répond plus.

GARDE-FOU LÉGAL (personnes physiques) : le flux public ne porte AUCUN champ de
type juridique — seule la « raisonsociale » distingue « NOM PRÉNOM » d'une
raison sociale. On n'inclut donc que les lignes dont la dénomination porte une
forme juridique de personne morale reconnue (liste ci-dessous). Règle
volontairement conservatrice : dans le doute, on EXCLUT. Les dénominations
anonymisées par l'ASP (totaux <= 1 250 €) sont exclues par la même règle.

NOTE : les reversements (mesures « R », montants négatifs) sont écartés par la
validation aval (montant > 0) — les totaux affichés sont donc légèrement
supérieurs aux montants nets ASP.
"""
from __future__ import annotations

import re

import requests

from ..normalize import dept_from_insee, make_record, to_year

BASE = "https://reporting.lda.asp-public.fr/Reporting/api"
# EF 2025 — cube « Paiements EF 2025 agrégés public - CSV » (à faire tourner
# chaque année, voir docstring).
PROJECT_ID = "5184E2D24047C6A70CCB9EAD5B7898BC"
CUBE_ID = "B5191748114FEF01B8FDE9A32D2D8D34"
SOURCE_NAME = "Bénéficiaires PAC — portail de reporting ASP"
SOURCE_URL = "https://agriculture.gouv.fr/les-beneficiaires-des-aides-de-la-pac"
TIMEOUT = 120
PAGE = 25_000

# Formes juridiques de personnes morales repérables dans la dénomination.
# En tête de mot uniquement (\b) pour éviter les faux positifs sur des noms.
_MORALE = re.compile(
    r"\b(GAEC|EARL|SCEA|SCEV|CUMA|GFA|SICA|SARL|EURL|SAS|SASU|SNC|SCI|GIE|SA|STE|"
    r"SOCIETE|GROUPEMENT|EXPLOITATION|ASSOCIATION|FONDATION|COOPERATIVE|SYNDICAT|"
    r"COMITE|CHAMBRE|INSTITUT|LYCEE|CONSERVATOIRE|DOMAINE|FERME|COMMUNE|MAIRIE|"
    r"COMMUNAUTE|DEPARTEMENT|REGION|ETABLISSEMENT|ETS)\b"
)
_EXPLOITATION = re.compile(r"\b(GAEC|EARL|SCEA|SCEV|CUMA|GFA|EXPLOITATION|DOMAINE|FERME)\b")
_ASSOCIATION = re.compile(r"\b(ASSOCIATION|FONDATION|SYNDICAT|COMITE)\b")

# Fonds déduit du code mesure (I/III/IV = FEAGA ; V/VI = FEADER ; cf. notice ASP).
_FEADER = ("V.", "VI.")


def _type_beneficiaire(nom: str) -> str | None:
    """Type déduit de la dénomination ; None = non identifiable -> exclu."""
    up = nom.upper()
    if not _MORALE.search(up):
        return None
    if _EXPLOITATION.search(up):
        return "exploitation"
    if _ASSOCIATION.search(up):
        return "association"
    return "entreprise"


def _login(session: requests.Session) -> None:
    r = session.post(f"{BASE}/auth/login", json={"loginMode": 8}, timeout=TIMEOUT)
    r.raise_for_status()
    session.headers["X-MSTR-AuthToken"] = r.headers["X-MSTR-AuthToken"]
    session.headers["X-MSTR-ProjectID"] = PROJECT_ID


def _rows(page: dict):
    """Itère (attributs, montant_mesure) sur une page de cube MicroStrategy."""
    attrs = page["definition"]["grid"]["rows"]
    names = [a["name"] for a in attrs]
    for hdr, metrics in zip(page["data"]["headers"]["rows"], page["data"]["metricValues"]["raw"]):
        values = {
            names[j]: attrs[j]["elements"][idx]["formValues"][0]
            for j, idx in enumerate(hdr)
        }
        yield values, metrics[0]  # métrique 0 = « montant net mesure »


def fetch() -> list[dict]:
    s = requests.Session()
    _login(s)

    records: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        r = s.post(
            f"{BASE}/v2/cubes/{CUBE_ID}/instances",
            params={"limit": PAGE, "offset": offset},
            json={},
            timeout=TIMEOUT,
        )
        if r.status_code == 404:
            raise RuntimeError(
                f"Cube PAC {CUBE_ID} introuvable : identifiants probablement tournés "
                f"avec le nouvel exercice — les relever sur {SOURCE_URL}"
            )
        r.raise_for_status()
        page = r.json()
        total = page["data"]["paging"]["total"]
        for values, montant in _rows(page):
            nom = (values.get("raisonsociale") or "").strip()
            type_ = _type_beneficiaire(nom)
            if type_ is None:  # personne physique ou anonymisé : exclu
                continue
            mesure = values.get("code type mesure denomination mesure") or ""
            fonds = "FEADER" if mesure.startswith(_FEADER) else "FEAGA"
            records.append(make_record(
                nom=nom,
                type_=type_,
                annee=to_year(values.get("annee publication")),
                montant=montant,
                objet=mesure,
                financeur_type="ue",
                financeur_nom=f"PAC — {fonds} (via ASP)",
                commune=(values.get("codepostal libellecommune") or "").split(" - ")[-1],
                departement=dept_from_insee(values.get("code insee")),
                pays="FR",
                source=SOURCE_NAME,
                source_url=SOURCE_URL,
                ref=values.get("id") or "",  # id interne ASP : unicité de la ligne
            ) | {"source_kind": "pac"})
        offset += PAGE

    if not records:
        raise RuntimeError("PAC : 0 personne morale extraite du cube ASP.")
    return records
