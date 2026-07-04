"""Schéma canonique commun à toutes les sources.

Toute source hétérogène (associations, PAC, aides d'État) est ramenée à ce
format unique avant classification et agrégation. C'est ce qui rend les
données comparables.

Un enregistrement = une ligne de subvention rattachée à un bénéficiaire.
"""
from __future__ import annotations

import hashlib
import re

# Types de bénéficiaires retenus. Les personnes physiques sont exclues par
# défaut pour des raisons légales (RGPD, CJUE 2010 sur la PAC). Voir ROADMAP.
TYPES = {"association", "entreprise", "exploitation"}


def clean_str(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def to_float(value) -> float | None:
    if value is None or value == "":
        return None
    s = str(value).replace("\u202f", "").replace(" ", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def to_year(value) -> int | None:
    if value is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    return int(m.group(0)) if m else None


def beneficiaire_id(nom: str, siren: str = "", rna: str = "") -> str:
    """Identifiant stable d'un bénéficiaire.

    On privilégie le SIREN, puis le RNA, puis un hash du nom normalisé.
    C'est cette clé qui permet de regrouper toutes les subventions d'un même
    bénéficiaire (et donc de calculer « depuis quand il touche cette aide »).
    """
    if siren:
        return f"siren:{siren}"
    if rna:
        return f"rna:{rna}"
    h = hashlib.sha1(clean_str(nom).lower().encode("utf-8")).hexdigest()[:12]
    return f"nom:{h}"


def make_record(
    *,
    nom: str,
    type_: str,
    annee: int | None,
    montant: float | None,
    objet: str = "",
    financeur_type: str = "",
    financeur_nom: str = "",
    programme: str = "",
    mission: str = "",
    siren: str = "",
    rna: str = "",
    naf: str = "",
    commune: str = "",
    pays: str = "FR",
    activite: str = "",
    source: str = "",
    source_url: str = "",
) -> dict:
    type_ = type_ if type_ in TYPES else "association"
    pays = (pays or "FR").upper()
    bid = beneficiaire_id(nom, siren, rna)
    rid = hashlib.sha1(
        f"{bid}|{annee}|{montant}|{objet}|{financeur_nom}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": rid,
        "annee": annee,
        "montant": montant,
        "objet": clean_str(objet),
        "financeur_type": financeur_type,
        "financeur_nom": clean_str(financeur_nom),
        "programme": clean_str(programme),
        "mission": clean_str(mission),
        # cofog / domaine sont remplis par classify.py
        "cofog": "",
        "domaine": "",
        "source": source,
        "source_url": source_url,
        "beneficiaire": {
            "id": bid,
            "nom": clean_str(nom),
            "type": type_,
            "siren": clean_str(siren),
            "rna": clean_str(rna),
            "naf": clean_str(naf),
            "commune": clean_str(commune),
            "pays": pays,
            "est_etranger": pays != "FR",
            "activite": clean_str(activite),
        },
    }


def valid(record: dict) -> bool:
    """Un enregistrement exploitable a au minimum un nom, un montant et une année."""
    return bool(
        record["beneficiaire"]["nom"]
        and record["montant"] is not None
        and record["montant"] > 0
        and record["annee"] is not None
    )
