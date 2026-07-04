"""Helpers partagés par les connecteurs de sources."""
from __future__ import annotations

import csv
import io
import unicodedata

import requests

# Pas d'User-Agent personnalisé : certains serveurs publics renvoient des
# réponses différentes (leçon Votre-vote). On reste sur le défaut requests.
TIMEOUT = 120


def http_get(url: str, params: dict | None = None) -> requests.Response:
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def datagouv_csv_resources(dataset_id: str) -> list[dict]:
    """Liste les ressources CSV d'un jeu de données data.gouv.fr via l'API."""
    url = f"https://www.data.gouv.fr/api/1/datasets/{dataset_id}/"
    data = http_get(url).json()
    out = []
    for res in data.get("resources", []):
        fmt = (res.get("format") or "").lower()
        if fmt in ("csv", "tsv") or (res.get("url", "").lower().endswith((".csv", ".tsv"))):
            out.append({"url": res["url"], "title": res.get("title", ""), "format": fmt})
    return out


def read_csv(text: str) -> list[dict]:
    """Lit un CSV en détectant automatiquement le délimiteur."""
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [row for row in reader]


def _norm_key(k: str) -> str:
    """Normalise un nom de colonne : casse, accents, BOM, espaces parasites.

    Les fichiers réels des collectivités déforment les en-têtes du schéma
    (« nomBénéficiaire », « Objet  », « iDRAE »…) — constaté sur les jeux
    SCDL publiés (Ille-et-Vilaine notamment).
    """
    k = unicodedata.normalize("NFD", k).encode("ascii", "ignore").decode()
    return k.lower().strip()


def pick(row: dict, *candidates: str) -> str:
    """Renvoie la première colonne présente parmi des noms candidats (souple
    face aux variations de nommage entre millésimes)."""
    norm = {_norm_key(k): v for k, v in row.items() if k}
    for c in candidates:
        v = norm.get(_norm_key(c))
        if v not in (None, ""):
            return v
    return ""
