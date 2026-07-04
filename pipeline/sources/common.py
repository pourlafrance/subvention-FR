"""Helpers partagés par les connecteurs de sources."""
from __future__ import annotations

import csv
import io
import unicodedata

import requests

# Pas d'User-Agent personnalisé : certains serveurs publics renvoient des
# réponses différentes (leçon Votre-vote). On reste sur le défaut requests.
# (connexion 30 s, lecture 120 s : un hôte mort ne bloque pas 2 min par fichier)
TIMEOUT = (30, 120)


def http_get(url: str, params: dict | None = None) -> requests.Response:
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def fetch_text(url: str) -> str:
    """Télécharge un fichier texte en devinant l'encodage de façon robuste.

    Le `.text` de requests se fie au header Content-Type, souvent absent ou
    faux sur les portails open data : on a constaté sur fichiers réels de
    l'UTF-8 avec BOM lu en cp1252 (« ï»¿nomAttribuant », Dordogne), et du
    cp850 hérité d'exports DOS/Excel (« COLLECTIVIT\\x90 », Bayonne).
    """
    content = http_get(url).content
    for enc in ("utf-8-sig", "cp1252", "cp850"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1")  # ne peut pas échouer


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
    try:
        return list(csv.DictReader(io.StringIO(text), delimiter=delim))
    except csv.Error:
        # Fins de ligne mixtes (« new-line character seen in unquoted field »,
        # constaté sur un export réel) : on normalise et on retente.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def _norm_key(k: str) -> str:
    """Normalise un nom de colonne : casse, accents, BOM, et tout caractère
    non alphanumérique (espaces, astérisques, underscores).

    Les fichiers réels des collectivités déforment les en-têtes du schéma —
    constaté sur les jeux SCDL publiés : « nomBénéficiaire », « Objet  »,
    « iDRAE » (Ille-et-Vilaine), « DATE CONVENTION » (Bayonne),
    « Date de convention* » (DILCRAH). Après normalisation, « nom_beneficiaire »,
    « nomBénéficiaire » et « NOM BENEFICIAIRE » deviennent tous « nombeneficiaire ».
    """
    k = unicodedata.normalize("NFD", k).encode("ascii", "ignore").decode()
    return "".join(c for c in k.lower() if c.isalnum())


def pick(row: dict, *candidates: str) -> str:
    """Renvoie la première colonne présente parmi des noms candidats (souple
    face aux variations de nommage entre millésimes)."""
    norm = {_norm_key(k): v for k, v in row.items() if k}
    for c in candidates:
        v = norm.get(_norm_key(c))
        if v not in (None, ""):
            return v
    return ""
