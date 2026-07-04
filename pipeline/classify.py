"""Classification : programme budgétaire -> division COFOG -> domaine public.

S'appuie sur pipeline/mapping/programme_cofog_domaine.csv. La règle est stricte
et déterministe : un programme donné tombe toujours dans le même domaine. Aucune
décision n'est prise « à la volée » ici — tout est dans la table, auditable.

Pour les sources sans programme budgétaire (PAC, aides d'État aux entreprises),
on applique un domaine par défaut documenté plutôt que de deviner.
"""
from __future__ import annotations

import csv
import os

MAPPING_PATH = os.path.join(os.path.dirname(__file__), "mapping", "programme_cofog_domaine.csv")

# Domaines par défaut pour les sources non rattachées à un programme État.
DEFAULTS = {
    "pac": ("04", "Agriculture — PAC"),
    "aide_etat_entreprise": ("04", "Économie — entreprises"),
    # Horizon Europe : R&D appliquée aux affaires économiques (COFOG 04.8).
    "ue_recherche": ("04", "Recherche et innovation — UE"),
    # ADEME : protection de l'environnement (COFOG 05) — approximation
    # assumée, une partie des aides relève de l'énergie (04).
    "agence_ademe": ("05", "Écologie — transition (ADEME)"),
    "inconnu": ("", "Non classé"),
}


def load_mapping(path: str = MAPPING_PATH) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    with open(path, encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
    reader = csv.DictReader(rows)
    for row in reader:
        code = (row.get("programme_code") or "").strip()
        if not code:
            continue
        mapping[code] = (
            (row.get("cofog_division") or "").strip(),
            (row.get("domaine_public") or "").strip(),
        )
    return mapping


def classify(record: dict, mapping: dict[str, tuple[str, str]]) -> dict:
    programme = (record.get("programme") or "").strip()
    if programme and programme in mapping:
        cofog, domaine = mapping[programme]
    elif record.get("source_kind") in DEFAULTS:
        cofog, domaine = DEFAULTS[record["source_kind"]]
    else:
        cofog, domaine = DEFAULTS["inconnu"]
    record["cofog"] = cofog
    record["domaine"] = domaine
    return record


def classify_all(records: list[dict], mapping: dict[str, tuple[str, str]] | None = None) -> list[dict]:
    mapping = mapping or load_mapping()
    return [classify(r, mapping) for r in records]
