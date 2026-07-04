"""Enrichissement des bénéficiaires via l'API Recherche d'entreprises.

https://recherche-entreprises.api.gouv.fr — API publique de l'État, sans clé.
Pour chaque SIREN présent dans les données, on récupère la fiche officielle
(base SIRENE) pour :

  - VALIDER le type déclaré par la source (une « association » dont la
    catégorie juridique est une société commerciale est requalifiée) ;
  - compléter NAF, commune, tranche d'effectifs, état administratif.

Politique : enrichissement fail-soft — une panne de l'API ne fait pas échouer
le run (ce n'est pas une source de vérité des montants), mais tout est compté
et affiché dans le résumé. On ne remplace JAMAIS une valeur présente dans la
source par une valeur API, on ne fait que compléter — sauf le type, où SIRENE
fait autorité sur la nature juridique.
"""
from __future__ import annotations

import json
import os
import time

import requests

ENDPOINT = "https://recherche-entreprises.api.gouv.fr/search"
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache", "entreprises.json")
TIMEOUT = 30
MAX_RPS = 6          # limite documentée : 7 req/s — on reste dessous
MAX_LOOKUPS = 2000   # plafond d'appels par run (les plus gros volumes d'abord)

# Tranche d'effectifs INSEE -> libellé lisible.
EFFECTIFS = {
    "00": "0 salarié", "01": "1 ou 2 salariés", "02": "3 à 5 salariés",
    "03": "6 à 9 salariés", "11": "10 à 19 salariés", "12": "20 à 49 salariés",
    "21": "50 à 99 salariés", "22": "100 à 199 salariés", "31": "200 à 249 salariés",
    "32": "250 à 499 salariés", "41": "500 à 999 salariés", "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés", "52": "5 000 à 9 999 salariés", "53": "10 000 salariés et plus",
}


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


HEADERS = {"User-Agent": "subventions-fr-etl (observatoire citoyen des subventions)"}
PARAMS = {"per_page": 1, "minimal": "true", "include": "siege,complements"}


def _fetch_siren(siren: str) -> dict | None:
    """Interroge l'API pour un SIREN. None = introuvable. Lève sur erreur réseau."""
    r = requests.get(ENDPOINT, params={"q": siren, **PARAMS}, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code == 429:  # limite de débit : on respecte Retry-After puis on retente une fois
        time.sleep(float(r.headers.get("Retry-After", 2)))
        r = requests.get(ENDPOINT, params={"q": siren, **PARAMS}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    for res in r.json().get("results", []):
        if res.get("siren") == siren:
            siege = res.get("siege") or {}
            comp = res.get("complements") or {}
            return {
                "nature_juridique": res.get("nature_juridique") or "",
                "est_association": bool(comp.get("est_association")),
                "naf": res.get("activite_principale") or "",
                "commune": siege.get("libelle_commune") or "",
                "effectifs": res.get("tranche_effectif_salarie") or "",
                "etat": res.get("etat_administratif") or "",
            }
    return None


def _type_sirene(info: dict) -> str | None:
    """Type déduit de la fiche SIRENE, si non ambigu.

    Le drapeau est_association de l'API fait foi ; sinon la catégorie
    juridique : 5xxx = société commerciale -> entreprise, 92xx = association.
    Les autres catégories (droit public, GIE…) ne permettent pas de trancher.
    """
    if info.get("est_association"):
        return "association"
    nj = info.get("nature_juridique") or ""
    if nj.startswith("5"):
        return "entreprise"
    if nj.startswith("92"):
        return "association"
    return None


def enrich_all(records: list[dict], max_lookups: int = MAX_LOOKUPS) -> dict:
    """Enrichit records en place. Renvoie les compteurs pour le résumé de run."""
    # SIRENs uniques, classés par volume décroissant : si on plafonne, on
    # enrichit d'abord ceux qui pèsent le plus dans les chiffres affichés.
    volume: dict[str, float] = {}
    for r in records:
        siren = r["beneficiaire"].get("siren") or ""
        if len(siren) == 9 and siren.isdigit():
            volume[siren] = volume.get(siren, 0) + (r["montant"] or 0)
    sirens = sorted(volume, key=lambda s: -volume[s])

    cache = _load_cache()
    a_interroger = [s for s in sirens if s not in cache][:max_lookups]
    ignores = max(0, len([s for s in sirens if s not in cache]) - max_lookups)

    stats = {"total_sirens": len(sirens), "appels": 0, "introuvables": 0,
             "erreurs": 0, "corrections_type": 0, "ignores_plafond": ignores}

    for siren in a_interroger:
        try:
            cache[siren] = _fetch_siren(siren)
            stats["appels"] += 1
            if cache[siren] is None:
                stats["introuvables"] += 1
        except Exception:
            stats["erreurs"] += 1
            cache.pop(siren, None)  # on retentera au prochain run
        time.sleep(1 / MAX_RPS)
    _save_cache(cache)

    for r in records:
        b = r["beneficiaire"]
        info = cache.get(b.get("siren") or "")
        if not info:
            continue
        # Complétion sans écrasement.
        if not b.get("naf") and info["naf"]:
            b["naf"] = info["naf"]
        if not b.get("commune") and info["commune"]:
            b["commune"] = info["commune"]
        if info["effectifs"] in EFFECTIFS:
            b["effectifs"] = EFFECTIFS[info["effectifs"]]
        if info["etat"]:
            b["etat_administratif"] = info["etat"]
        # Le type : SIRENE fait autorité quand la catégorie juridique tranche.
        type_sirene = _type_sirene(info)
        if type_sirene and type_sirene != b["type"] and b["type"] != "exploitation":
            b["type"] = type_sirene
            stats["corrections_type"] += 1
    return stats
