"""Contrôles de cohérence des données produites (fail-loud).

Contrôle croisé COFOG : pour chaque division COFOG et chaque année, le volume
de subventions documenté ici ne peut pas dépasser la dépense TOTALE des
administrations publiques pour cette division (comptes nationaux). Si c'est le
cas, c'est un double comptage ou une erreur d'unité — le run doit échouer.

La référence est versionnée dans mapping/controle_cofog_apu.csv (voir son
en-tête pour la source). Si le fichier est absent ou vide, le contrôle est
sauté avec un avertissement : on ne bloque pas sur une référence manquante,
mais on ne valide jamais silencieusement non plus.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

REF_PATH = os.path.join(os.path.dirname(__file__), "mapping", "controle_cofog_apu.csv")


def load_reference(path: str = REF_PATH) -> dict[str, float]:
    """Division COFOG -> dépense annuelle totale des APU (euros)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
    ref: dict[str, float] = {}
    for row in csv.DictReader(rows):
        div = (row.get("cofog_division") or "").strip()
        val = (row.get("depense_apu_meur") or "").strip()
        if div and val:
            ref[div.zfill(2)] = float(val) * 1_000_000  # M€ -> €
    return ref


def check_cofog(records: list[dict]) -> list[str]:
    """Retourne la liste des anomalies (vide = contrôle passé ou sauté)."""
    ref = load_reference()
    if not ref:
        print("::warning::Contrôle COFOG sauté : mapping/controle_cofog_apu.csv absent ou vide.")
        return []
    par_div_annee: dict[tuple[str, int], float] = defaultdict(float)
    for r in records:
        if r.get("cofog") and r.get("annee") and r.get("montant"):
            par_div_annee[(r["cofog"].zfill(2), r["annee"])] += r["montant"]
    anomalies = []
    for (div, annee), total in sorted(par_div_annee.items()):
        plafond = ref.get(div)
        if plafond and total > plafond:
            anomalies.append(
                f"COFOG {div}, année {annee} : {round(total / 1e6)} M€ documentés "
                f"> {round(plafond / 1e6)} M€ de dépense APU totale (comptes nationaux). "
                "Double comptage ou erreur d'unité probable."
            )
    return anomalies
