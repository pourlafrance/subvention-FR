"""Agrégation : produit stats.json, le petit fichier d'agrégats lu par l'accueil.

Tous les calculs lourds (GROUP BY) sont faits ici, en CI, une fois. Le
navigateur ne fait jamais d'agrégation : il charge stats.json directement.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import date

IPC_PATH = os.path.join(os.path.dirname(__file__), "mapping", "ipc_insee.csv")

# Références macro pour l'estimation de la part non publiée (à sourcer / affiner).
# Sénat, commission d'enquête 2025 : ~211 Md€/an d'aides aux entreprises.
# Jaune budgétaire associations : ordre de grandeur ~8,5 Md€ État + collectivités.
REF_TOTAL_ENTREPRISES_EUR = 211_000_000_000
REF_TOTAL_ASSOCIATIONS_EUR = 23_000_000_000


def _sum(records, pred):
    return sum(r["montant"] for r in records if pred(r) and r["montant"])


def load_ipc(path: str = IPC_PATH) -> dict[int, float]:
    """Table IPC INSEE (moyennes annuelles) pour la déflation en euros constants.

    Fichier versionné et sourcé dans mapping/ (voir son en-tête). S'il est
    absent, la série en euros constants est simplement omise — jamais inventée.
    """
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
    return {int(row["annee"]): float(row["ipc"]) for row in csv.DictReader(rows)}


def build_stats(records: list[dict], *, is_sample: bool, sources: list[dict]) -> dict:
    annees = sorted({r["annee"] for r in records if r["annee"]})
    annee_max = annees[-1] if annees else None
    # Année de référence des agrégats « dernière année » : la plus récente qui
    # soit à la fois NON future et couverte par PLUSIEURS sources. Les années
    # futures (engagements pluriannuels CORDIS/SCDL datés de l'année de début)
    # et les années en cours alimentées par une seule source ne sont pas
    # représentatives d'un exercice — constaté au 1er run réel (« 2027 » puis
    # « 2026 » ne portaient que CORDIS).
    annee_courante = date.today().year
    sources_par_annee = defaultdict(set)
    for r in records:
        if r["annee"]:
            sources_par_annee[r["annee"]].add(r.get("source_kind") or r.get("source") or "?")
    candidates = [a for a in annees if a <= annee_courante and len(sources_par_annee[a]) >= 2]
    if not candidates:
        candidates = [a for a in annees if a <= annee_courante]
    annee_ref = candidates[-1] if candidates else annee_max

    assos = [r for r in records if r["beneficiaire"]["type"] == "association"]
    ents = [r for r in records if r["beneficiaire"]["type"] in ("entreprise", "exploitation")]

    def count_benef(rs):
        return len({r["beneficiaire"]["id"] for r in rs})

    # Volume par année (toutes catégories), en euros courants et — si la table
    # IPC couvre l'année — en euros constants de la dernière année connue.
    par_annee = defaultdict(float)
    for r in records:
        if r["annee"] and r["montant"]:
            par_annee[r["annee"]] += r["montant"]
    ipc = load_ipc()
    ipc_ref = ipc.get(annee_ref)
    volume_annuel = []
    for a in annees:
        entry = {"annee": a, "montant": round(par_annee[a], 2)}
        if ipc_ref and ipc.get(a):
            entry["montant_constant"] = round(par_annee[a] * ipc_ref / ipc[a], 2)
        volume_annuel.append(entry)

    # Répartition par domaine (année de référence, pour le graphe d'accueil)
    dom = defaultdict(lambda: {"volume_eur": 0.0, "count": 0, "cofog": ""})
    for r in records:
        if annee_ref and r["annee"] != annee_ref:
            continue
        d = r["domaine"] or "Non classé"
        dom[d]["volume_eur"] += r["montant"] or 0
        dom[d]["count"] += 1
        dom[d]["cofog"] = r["cofog"]
    domaines = [
        {"domaine": k, "cofog": v["cofog"], "volume_eur": round(v["volume_eur"], 2), "count": v["count"]}
        for k, v in sorted(dom.items(), key=lambda kv: -kv[1]["volume_eur"])
    ]

    # Top bénéficiaires (toutes années) : la question que tout visiteur se pose.
    # Uniquement des personnes morales (garantie par le schéma), donc publiable.
    par_benef = {}
    for r in records:
        b = r["beneficiaire"]
        e = par_benef.setdefault(b["id"], {
            "id": b["id"], "nom": b["nom"], "type": b["type"],
            "total_eur": 0.0, "n": 0,
        })
        e["total_eur"] += r["montant"] or 0
        e["n"] += 1
    top_beneficiaires = sorted(par_benef.values(), key=lambda e: -e["total_eur"])[:10]
    for e in top_beneficiaires:
        e["total_eur"] = round(e["total_eur"], 2)

    # Recouvrement inter-sources : un même bénéficiaire présent dans plusieurs
    # sources peut signaler un co-financement compté deux fois (État + UE, ou
    # État + collectivité). On ne déduplique pas silencieusement — on compte et
    # on affiche (principe : montrer les taux de couverture, pas les masquer).
    sources_par_benef = defaultdict(set)
    for r in records:
        sources_par_benef[r["beneficiaire"]["id"]].add(r.get("source_kind") or r.get("source") or "?")
    multi = {bid for bid, srcs in sources_par_benef.items() if len(srcs) > 1}
    vol_multi = _sum(records, lambda r: r["beneficiaire"]["id"] in multi)
    recouvrement = {
        "beneficiaires_multi_sources": len(multi),
        "volume_concerne_eur": round(vol_multi, 2),
        "note": "Bénéficiaires présents dans plusieurs sources : volume potentiellement "
                "compté plusieurs fois en cas de co-financement. Signalé, non déduit.",
    }

    # Volume vers des bénéficiaires hors France (limite documentée : enregistrement
    # à l'étranger, pas nationalité du capital).
    vol_etranger = _sum(records, lambda r: r["beneficiaire"]["est_etranger"])
    vol_total = _sum(records, lambda r: True)

    # Estimation part visible / part totale estimée.
    visible_ent = _sum(ents, lambda r: True)
    visible_asso = _sum(assos, lambda r: True)
    estime_total = REF_TOTAL_ENTREPRISES_EUR + REF_TOTAL_ASSOCIATIONS_EUR
    part_visible = (visible_ent + visible_asso) / estime_total if estime_total else None

    return {
        "meta": {
            "is_sample": is_sample,
            "annee_min": annees[0] if annees else None,
            "annee_max": annee_max,
            "annee_ref": annee_ref,
            "n_records": len(records),
            "sources": sources,
            "recouvrement": recouvrement,
            "euros_constants": (
                {"base_annee": annee_ref,
                 "source": "IPC INSEE, moyennes annuelles base 2015 (idbank 001764363)"}
                if ipc_ref else None
            ),
        },
        "kpi": {
            "associations": {"count": count_benef(assos), "volume_eur": round(visible_asso, 2)},
            "entreprises": {"count": count_benef(ents), "volume_eur": round(visible_ent, 2)},
            "volume_total_annuel": volume_annuel,
            "etranger": {
                "volume_eur": round(vol_etranger, 2),
                "share": round(vol_etranger / vol_total, 4) if vol_total else 0,
            },
            "estimation": {
                "volume_visible_eur": round(visible_ent + visible_asso, 2),
                "volume_estime_total_eur": estime_total,
                "part_visible": round(part_visible, 4) if part_visible else None,
                "note": "Estimation : part publiée rapportée aux ordres de grandeur connus "
                        "(Sénat 2025 pour les entreprises, jaune budgétaire pour les associations).",
            },
        },
        "domaines": domaines,
        "top_beneficiaires": top_beneficiaires,
        # Valeurs de filtres précalculées sur la TOTALITÉ des données : la
        # couche SQLite ne fait jamais de DISTINCT plein-scan côté navigateur.
        "filters": {
            "domaines": sorted({r["domaine"] for r in records if r["domaine"]}),
            "annees": sorted(annees, reverse=True),
        },
    }
