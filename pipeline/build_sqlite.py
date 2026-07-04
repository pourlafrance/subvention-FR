"""Construit la base SQLite interrogée dans le navigateur via sql.js-httpvfs.

Points clés pour que les requêtes HTTP Range soient efficaces :
  - page_size = 1024 (réduit le surcoût par requête)
  - index couvrants sur les colonnes filtrées/triées
  - table FTS5 pour la recherche plein texte (jamais de LIKE '%...%')
  - VACUUM final pour appliquer le page_size et compacter

La base est ensuite (optionnellement) découpée en chunks par le script
sql.js-httpvfs côté front si elle dépasse 100 Mo (limite de fichier GitHub).
"""
from __future__ import annotations

import os
import sqlite3


def build(records: list[dict], out_path: str) -> dict:
    if os.path.exists(out_path):
        os.remove(out_path)
    con = sqlite3.connect(out_path)
    cur = con.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode = delete;
        PRAGMA page_size = 1024;

        CREATE TABLE beneficiaire (
            id TEXT PRIMARY KEY,
            nom TEXT, type TEXT, siren TEXT, rna TEXT, naf TEXT,
            commune TEXT, pays TEXT, est_etranger INTEGER, activite TEXT,
            effectifs TEXT,
            premiere_annee INTEGER, total_eur REAL, n_subventions INTEGER
        );

        CREATE TABLE subvention (
            id TEXT PRIMARY KEY,
            beneficiaire_id TEXT,
            annee INTEGER, montant REAL, objet TEXT,
            financeur_type TEXT, financeur_nom TEXT,
            programme TEXT, mission TEXT, cofog TEXT, domaine TEXT,
            source TEXT, source_url TEXT
        );

        CREATE INDEX idx_sub_benef ON subvention(beneficiaire_id);
        CREATE INDEX idx_sub_domaine ON subvention(domaine, montant DESC);
        CREATE INDEX idx_sub_annee ON subvention(annee, montant DESC);
        CREATE INDEX idx_sub_montant ON subvention(montant DESC);
        CREATE INDEX idx_benef_type ON beneficiaire(type, total_eur DESC);
        CREATE INDEX idx_benef_etranger ON beneficiaire(est_etranger, total_eur DESC);

        CREATE VIRTUAL TABLE recherche USING fts5(
            subvention_id UNINDEXED, beneficiaire_id UNINDEXED, nom, objet,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )

    # Agrège les bénéficiaires (premiere_annee = « depuis quand »)
    benef: dict[str, dict] = {}
    for r in records:
        b = r["beneficiaire"]
        e = benef.setdefault(b["id"], {**b, "premiere_annee": r["annee"], "total_eur": 0.0, "n": 0})
        if r["annee"] and (e["premiere_annee"] is None or r["annee"] < e["premiere_annee"]):
            e["premiere_annee"] = r["annee"]
        e["total_eur"] += r["montant"] or 0
        e["n"] += 1

    cur.executemany(
        "INSERT INTO beneficiaire VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (e["id"], e["nom"], e["type"], e["siren"], e["rna"], e["naf"], e["commune"],
             e["pays"], 1 if e["est_etranger"] else 0, e["activite"], e.get("effectifs", ""),
             e["premiere_annee"], round(e["total_eur"], 2), e["n"])
            for e in benef.values()
        ],
    )
    cur.executemany(
        "INSERT INTO subvention VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (r["id"], r["beneficiaire"]["id"], r["annee"], r["montant"], r["objet"],
             r["financeur_type"], r["financeur_nom"], r["programme"], r["mission"],
             r["cofog"], r["domaine"], r["source"], r["source_url"])
            for r in records
        ],
    )
    cur.executemany(
        "INSERT INTO recherche VALUES (?,?,?,?)",
        [(r["id"], r["beneficiaire"]["id"], r["beneficiaire"]["nom"], r["objet"]) for r in records],
    )
    con.commit()
    cur.execute("VACUUM;")
    con.commit()
    size = os.path.getsize(out_path)
    con.close()
    return {"path": out_path, "bytes": size, "beneficiaires": len(benef), "subventions": len(records)}
