"""Orchestrateur du pipeline de données. À lancer depuis la racine du dépôt :

    python -m pipeline.build

Étapes : fetch (par source) -> normalise -> classe (COFOG) -> agrège
-> écrit public/data/stats.json, subventions.json et subventions.db.

Politique « fail-loud » : toute erreur de source fait échouer le run (exit 1),
pour qu'un run vert signale de vraies données. Des annotations ::notice::/::error::
résument les volumes sans dérouler les logs.
"""
from __future__ import annotations

import json
import os
import sys

from .aggregate import build_stats
from .checks import check_cofog
from .classify import classify_all, load_mapping
from .enrich import enrich_all
from .normalize import valid
from .sources import aides_etat, associations, europe_cordis, jaune_associations, pac
from .build_sqlite import build as build_sqlite

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "public", "data")
JSON_MAX_RECORDS = 50_000  # au-delà, on s'appuie sur SQLite (httpvfs) plutôt que JSON

SOURCES = [
    ("Associations (données essentielles SCDL)", associations.fetch),
    ("Jaune budgétaire associations", jaune_associations.fetch),
    ("PAC (portail ASP)", pac.fetch),
    ("Aides d'État (TAM)", aides_etat.fetch),
    ("Horizon Europe (CORDIS)", europe_cordis.fetch),
]


def notice(msg: str):
    print(f"::notice::{msg}")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    records: list[dict] = []
    used_sources: list[dict] = []

    for name, fn in SOURCES:
        try:
            recs = fn()
        except Exception as exc:  # fail-loud
            print(f"::error::Source '{name}' en échec : {exc}")
            return 1
        recs = [r for r in recs if valid(r)]
        notice(f"Source '{name}' : {len(recs)} enregistrements valides")
        used_sources.append({"nom": name, "n": len(recs)})
        records.extend(recs)

    if not records:
        print("::error::Aucun enregistrement collecté, toutes sources confondues.")
        return 1

    # Enrichissement SIRENE (fail-soft, désactivable : SUBV_ENRICH=0).
    if os.environ.get("SUBV_ENRICH", "1") != "0":
        e = enrich_all(records)
        notice(f"Enrichissement SIRENE : {e['total_sirens']} SIREN, {e['appels']} appels, "
               f"{e['corrections_type']} types corrigés, {e['introuvables']} introuvables, "
               f"{e['erreurs']} erreurs, {e['ignores_plafond']} au-delà du plafond")

    # Dédoublonnage par id (bénéficiaire|année|montant|objet|financeur|ref) :
    # ne fusionne que les lignes STRICTEMENT identiques — typiquement une même
    # convention publiée dans plusieurs jeux SCDL. Compté, jamais silencieux.
    uniques: dict[str, dict] = {}
    for r in records:
        uniques.setdefault(r["id"], r)
    n_doublons = len(records) - len(uniques)
    records = list(uniques.values())
    if n_doublons:
        notice(f"Dédoublonnage : {n_doublons} lignes strictement identiques fusionnées")

    records = classify_all(records, load_mapping())
    n_classes = sum(1 for r in records if r["domaine"] and r["domaine"] != "Non classé")
    notice(f"Classification : {n_classes}/{len(records)} rattachés à un domaine "
           f"({round(100 * n_classes / len(records))}%)")

    # Contrôle croisé : nos totaux ne peuvent pas dépasser la dépense publique
    # totale par fonction (comptes nationaux). Fail-loud si c'est le cas.
    anomalies = check_cofog(records)
    if anomalies:
        for a in anomalies:
            print(f"::error::{a}")
        return 1

    info = build_sqlite(records, os.path.join(OUT_DIR, "subventions.db"))
    notice(f"subventions.db : {info['subventions']} subventions, "
           f"{info['beneficiaires']} bénéficiaires, {round(info['bytes']/1e6, 1)} Mo")

    detail_json = len(records) <= JSON_MAX_RECORDS
    stats = build_stats(records, is_sample=False, sources=used_sources)
    # La couche détail que le front doit utiliser, et la taille exacte de la
    # base (fileLength explicite pour sql.js-httpvfs : le gzip de GitHub Pages
    # fausse la détection de taille par HEAD).
    stats["meta"]["detail"] = "json" if detail_json else "sqlite"
    stats["meta"]["db_bytes"] = info["bytes"]
    _write_json(os.path.join(OUT_DIR, "stats.json"), stats)
    notice(f"stats.json écrit — {stats['meta']['n_records']} lignes, "
           f"{len(stats['domaines'])} domaines, détail via {stats['meta']['detail']}")

    if detail_json:
        _write_json(os.path.join(OUT_DIR, "subventions.json"), records)
        notice(f"subventions.json écrit ({len(records)} lignes)")
    else:
        json_path = os.path.join(OUT_DIR, "subventions.json")
        if os.path.exists(json_path):
            os.remove(json_path)
        notice(f"subventions.json ignoré (>{JSON_MAX_RECORDS}) — le front bascule sur SQLite")
    return 0


def _write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    sys.exit(main())
