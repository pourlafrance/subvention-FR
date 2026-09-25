"""Source : bénéficiaires des aides de la PAC (FEAGA/FEADER), publiés par l'ASP.

Cadre : règlement (UE) 2021/2116, publication annuelle par exercice financier
(16/10/N-1 -> 15/10/N), rétention 2 ans. Il n'existe PAS de jeu exploitable sur
data.gouv.fr (vérifié 2026-07 : l'organisation ASP n'y publie que des archives
2005-2013). La vraie source est le portail de reporting de l'ASP, lié depuis
https://agriculture.gouv.fr/les-beneficiaires-des-aides-de-la-pac

Accès programmatique validé sur données réelles (2026-09) : API REST
MicroStrategy du portail, session anonyme (loginMode 8, sans credentials). Depuis
2026, le compte invité n'a plus le droit d'interroger directement le cube
(erreur 403, « Execute access » refusé) : on lit le TABLEAU DE BORD public de
l'exercice, exactement comme le navigateur d'un visiteur, en pages de 25 000
lignes. Grain : bénéficiaire x mesure ; ~1,3 M lignes pour l'EF 2025.

DÉCOUVERTE AUTOMATIQUE : la page agriculture.gouv.fr ci-dessus porte un lien par
exercice (« Paiements du 16 octobre N-1 au 15 octobre N »). Le connecteur retient
le plus récent, lit la configuration de l'application (identifiant du tableau de
bord d'accueil), puis la définition du tableau de bord (grille). Plus aucun
identifiant n'est à tourner à la main ; les constantes ci-dessous ne servent que
de repli si la page du ministère est illisible. Fail-loud si rien ne répond.

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

from ..normalize import dept_from_insee, make_record

BASE = "https://reporting.lda.asp-public.fr/Reporting/api"
# Repli (EF 2025) si la page du ministère est illisible : application « Publication des
# bénéficiaires EF 2025 » du projet TRANSPARENCE. Voir DÉCOUVERTE AUTOMATIQUE.
PROJECT_ID = "5184E2D24047C6A70CCB9EAD5B7898BC"
APP_ID = "80F3CAEC9A624CA39091D245B38187A9"
EXERCICE = 2025
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


_LIEN = re.compile(
    r'<a [^>]*href="(https://reporting\.lda\.asp-public\.fr/Reporting/(?:CustomApp\?id=|app/config/)'
    r'([0-9A-F]{32}))"[^>]*>\s*(.*?)\s*</a>', re.S)
_PERIODE = re.compile(r"15\s+octobre\s+(\d{4})")


def _decouvrir_application() -> tuple[str, int]:
    """(identifiant d'application, exercice) du dernier exercice publié ; repli sur les constantes."""
    try:
        r = requests.get(SOURCE_URL, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        trouves = []
        for _url, app_id, libelle in _LIEN.findall(r.text):
            m = _PERIODE.search(re.sub(r"<[^>]+>", " ", libelle))
            if m:
                trouves.append((int(m.group(1)), app_id))
        if trouves:
            exercice, app_id = max(trouves)
            return app_id, exercice
    except requests.RequestException as e:
        print(f"::warning::PAC : page du ministère illisible ({e}) ; identifiants de repli utilisés")
    return APP_ID, EXERCICE


def _login(session: requests.Session, project_id: str) -> None:
    r = session.post(f"{BASE}/auth/login", json={"loginMode": 8}, timeout=TIMEOUT)
    r.raise_for_status()
    session.headers["X-MSTR-AuthToken"] = r.headers["X-MSTR-AuthToken"]
    session.headers["X-MSTR-ProjectID"] = project_id


def _tableau_de_bord(session: requests.Session, app_id: str) -> tuple[str, str, str, str]:
    """(projet, tableau de bord, chapitre, visualisation) de la première grille de l'application."""
    r = session.get(f"{BASE}/v2/applications/{app_id}", timeout=TIMEOUT)
    r.raise_for_status()
    url = r.json()["homeScreen"]["homeDocument"]["url"]  # « app/<projet>/<tableau de bord> »
    _, projet, dossier = url.split("/")
    session.headers["X-MSTR-ProjectID"] = projet
    r = session.get(f"{BASE}/v2/dossiers/{dossier}/definition", timeout=TIMEOUT)
    r.raise_for_status()
    for chapitre in r.json()["chapters"]:
        for page in chapitre.get("pages", []):
            for viz in page.get("visualizations", []):
                if viz.get("visualizationType") == "grid":
                    return projet, dossier, chapitre["key"], viz["key"]
    raise RuntimeError(f"PAC : aucune grille dans le tableau de bord {dossier} de l'application {app_id}.")


def _rows(page: dict):
    """Itère (attributs, montant) sur une page de grille MicroStrategy (mêmes structures que les cubes)."""
    attrs = page["definition"]["grid"]["rows"]
    names = [a["name"] for a in attrs]
    for hdr, metrics in zip(page["data"]["headers"]["rows"], page["data"]["metricValues"]["raw"]):
        values = {
            names[j]: attrs[j]["elements"][idx]["formValues"][0]
            for j, idx in enumerate(hdr)
        }
        yield values, metrics[0]  # métrique 0 = « Montant »


def _val(values: dict, *noms: str) -> str:
    """Valeur d'un attribut par nom, sans tenir compte de la casse ni des espaces (les libellés ont changé en 2026)."""
    index = {re.sub(r"\s+", "", k).lower(): v for k, v in values.items()}
    for nom in noms:
        v = index.get(re.sub(r"\s+", "", nom).lower())
        if v not in (None, ""):
            return str(v)
    return ""


def fetch() -> list[dict]:
    app_id, exercice = _decouvrir_application()
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    _login(s, PROJECT_ID)
    projet, dossier, chapitre, viz = _tableau_de_bord(s, app_id)
    r = s.post(f"{BASE}/dossiers/{dossier}/instances", json={}, timeout=TIMEOUT)
    r.raise_for_status()
    instance = r.json()["mid"]
    print(f"::notice::PAC : exercice {exercice}, application {app_id}, tableau de bord {dossier}")

    records: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        r = s.get(
            f"{BASE}/v2/dossiers/{dossier}/instances/{instance}/chapters/{chapitre}/visualizations/{viz}",
            params={"limit": PAGE, "offset": offset},
            timeout=TIMEOUT,
        )
        if r.status_code in (403, 404):
            raise RuntimeError(
                f"PAC : tableau de bord {dossier} inaccessible ({r.status_code}) : l'ASP a changé "
                f"l'application ou ses droits — vérifier les liens sur {SOURCE_URL}"
            )
        r.raise_for_status()
        page = r.json()
        total = page["data"]["paging"]["total"]
        for values, montant in _rows(page):
            nom = _val(values, "Raison sociale", "raisonsociale").strip()
            type_ = _type_beneficiaire(nom)
            if type_ is None:  # personne physique ou anonymisé : exclu
                continue
            mesure = _val(values, "Types d'interventions / mesures", "code type mesure denomination mesure")
            fonds = "FEADER" if mesure.startswith(_FEADER) else "FEAGA"
            records.append(make_record(
                nom=nom,
                type_=type_,
                annee=exercice,
                montant=montant,
                objet=mesure,
                financeur_type="ue",
                financeur_nom=f"PAC — {fonds} (via ASP)",
                commune=_val(values, "Commune", "codepostal libellecommune").split(" - ")[-1],
                departement=dept_from_insee(_val(values, "Code Insee", "code insee")),
                pays="FR",
                source=SOURCE_NAME,
                source_url=SOURCE_URL,
                # bénéficiaire x mesure x lieu : un même organisme peut recevoir le même montant
                # dans plusieurs communes (établissements distincts) : sans le lieu, ces versements
                # légitimes auraient le même identifiant.
                ref="|".join((_val(values, 'Idbeneficiaire', 'id'), mesure,
                              _val(values, 'Code postal', 'codepostal'), _val(values, 'Commune', 'codepostal libellecommune'))),
            ) | {"source_kind": "pac"})
        offset += PAGE

    if not records:
        raise RuntimeError("PAC : 0 personne morale extraite du tableau de bord ASP.")
    return records
