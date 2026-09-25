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
DF_PATH = os.path.join(os.path.dirname(__file__), "mapping", "depenses_fiscales_plf2023.csv")

# Référence macro pour l'estimation de la part non publiée.
# Sénat, commission d'enquête sur les aides publiques aux entreprises, rapport n° 808
# (2024-2025), déposé le 1er juillet 2025 : « au moins 211 milliards d'euros » d'aides aux
# entreprises en 2023, au sens large, présentés comme un ordre de grandeur :
# https://www.senat.fr/rap/r24-808-1/r24-808-1_mono.html
# Le rapport ne chiffre que les entreprises : aucun total sourcé n'est retenu pour les
# associations, et la comparaison se fait à année (2023) et périmètre (entreprises) identiques.
REF_TOTAL_ENTREPRISES_EUR = 211_000_000_000
REF_ANNEE_ENTREPRISES = 2023

# Libellés lisibles des sources pour les agrégats (clé = source_kind).
SOURCE_LABELS = {
    "association": "Données essentielles (SCDL)",
    "jaune_associations": "Jaune budgétaire (État)",
    "pac": "PAC (FEAGA/FEADER)",
    "aide_etat_entreprise": "Aides d'État (TAM)",
    "ue_recherche": "Horizon Europe",
    "agence_ademe": "ADEME",
}


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


def load_depenses_fiscales(path: str = DF_PATH) -> dict | None:
    """Agrège la table des dépenses fiscales (voir l'en-tête du fichier).

    Renvoie le total chiffré des dispositifs bénéficiant aux entreprises
    (réalisation 2021, colonne la plus complète) — la part de l'argent qui
    « sort » sans qu'aucun bénéficiaire ne soit publié.
    """
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
    total, n_chiffres, n_total = 0.0, 0, 0
    for row in csv.DictReader(rows, delimiter=";"):
        if "Entreprises" not in (row.get("beneficiaires_nature") or ""):
            continue
        n_total += 1
        val = (row.get("chiffrage_2021_realisation_Meur") or "").strip()
        try:
            total += float(val.replace(",", "."))
            n_chiffres += 1
        except ValueError:
            continue  # « - », « ε », « nc » : non sommables, comptés dans n_total
    return {
        "total_entreprises_eur": round(total * 1_000_000, 2),
        "n_dispositifs": n_total,
        "n_chiffres": n_chiffres,
        "annee_chiffrage": 2021,
        "source": "PLF 2023, annexe Voies et moyens tome II (réalisation 2021)",
    }


def build_stats(records: list[dict], *, is_sample: bool, sources: list[dict]) -> dict:
    annees = sorted({r["annee"] for r in records if r["annee"]})
    annee_max = annees[-1] if annees else None
    # Année de référence des agrégats « dernière année » : le dernier exercice
    # RÉVOLU couvert par PLUSIEURS sources. Ni les années futures (engagements
    # pluriannuels CORDIS/SCDL datés de l'année de début), ni l'année en cours
    # (partiellement alimentée), ni une année mono-source ne représentent un
    # exercice — constaté aux premiers runs réels (« 2027 », puis « 2026 »).
    annee_courante = date.today().year
    sources_par_annee = defaultdict(set)
    for r in records:
        if r["annee"]:
            sources_par_annee[r["annee"]].add(r.get("source_kind") or r.get("source") or "?")
    candidates = [a for a in annees if a < annee_courante and len(sources_par_annee[a]) >= 2]
    if not candidates:
        candidates = [a for a in annees if a < annee_courante] or [a for a in annees if a <= annee_courante]
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

    # Ventilation par source : une courbe « total » serait trompeuse quand la
    # couverture varie d'une année à l'autre (le jaune ne couvre que 2023, la
    # PAC 2024-2025…). Le graphe d'accueil empile ces séries pour rendre
    # l'élargissement des données visible au lieu de le confondre avec une
    # évolution de l'effort public.
    par_source_annee = defaultdict(lambda: defaultdict(float))
    for r in records:
        if r["annee"] and r["montant"]:
            libelle = SOURCE_LABELS.get(r.get("source_kind"), r.get("source") or "Autre")
            par_source_annee[libelle][r["annee"]] += r["montant"]
    volume_par_source = [
        {"source": src, "serie": [{"annee": a, "montant": round(m, 2)}
                                  for a, m in sorted(vals.items())]}
        for src, vals in sorted(par_source_annee.items())
    ]

    # Répartition par domaine sur TOUTE la période documentée : avec une
    # couverture hétérogène (le jaune ne couvre que 2023, la PAC 2024-2025…),
    # ancrer sur une seule année masquerait la diversité réelle des domaines.
    dom = defaultdict(lambda: {"volume_eur": 0.0, "count": 0, "cofog": ""})
    for r in records:
        d = r["domaine"] or "Non classé"
        dom[d]["volume_eur"] += r["montant"] or 0
        dom[d]["count"] += 1
        dom[d]["cofog"] = r["cofog"]
    domaines = [
        {"domaine": k, "cofog": v["cofog"], "volume_eur": round(v["volume_eur"], 2), "count": v["count"]}
        for k, v in sorted(dom.items(), key=lambda kv: -kv[1]["volume_eur"])
    ]

    # Répartition territoriale par département (siège du bénéficiaire).
    # Couverture partielle assumée : le taux de géolocalisation est publié
    # avec la carte, jamais un total présenté comme exhaustif.
    par_dept = defaultdict(lambda: {"volume_eur": 0.0, "count": 0})
    vol_geo = 0.0
    for r in records:
        dept = r["beneficiaire"].get("departement")
        if dept and r["montant"]:
            par_dept[dept]["volume_eur"] += r["montant"]
            par_dept[dept]["count"] += 1
            vol_geo += r["montant"]
    departements = [
        {"code": k, "volume_eur": round(v["volume_eur"], 2), "count": v["count"]}
        for k, v in sorted(par_dept.items(), key=lambda kv: -kv[1]["volume_eur"])
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

    # Estimation : aides aux entreprises documentées pour l'année de référence du Sénat,
    # rapportées à l'estimation du Sénat pour cette même année (même périmètre).
    visible_ent = _sum(ents, lambda r: True)
    visible_asso = _sum(assos, lambda r: True)
    visible_ent_ref = _sum(ents, lambda r: r["annee"] == REF_ANNEE_ENTREPRISES)
    estime_total = REF_TOTAL_ENTREPRISES_EUR
    part_visible = visible_ent_ref / estime_total if estime_total else None

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
            "volume_par_source": volume_par_source,
            "etranger": {
                "volume_eur": round(vol_etranger, 2),
                "share": round(vol_etranger / vol_total, 4) if vol_total else 0,
            },
            "estimation": {
                "volume_visible_eur": round(visible_ent_ref, 2),
                "volume_estime_total_eur": estime_total,
                "part_visible": round(part_visible, 4) if part_visible else None,
                "annee_reference": REF_ANNEE_ENTREPRISES,
                "perimetre": "entreprises",
                # Décomposition de l'invisible : les dépenses fiscales sortent
                # sans bénéficiaire nominatif, coût connu par dispositif.
                "depenses_fiscales": load_depenses_fiscales(),
                "note": "Aides aux entreprises documentées pour 2023, rapportées à l'estimation du "
                        "Sénat (rapport n° 808, 2025) pour la même année : ordre de grandeur, plancher "
                        "(toutes les sources ne couvrent pas 2023).",
            },
        },
        "domaines": domaines,
        "departements": {
            "liste": departements,
            "part_geolocalisee": round(vol_geo / vol_total, 4) if vol_total else 0,
        },
        "top_beneficiaires": top_beneficiaires,
        # Valeurs de filtres précalculées sur la TOTALITÉ des données : la
        # couche SQLite ne fait jamais de DISTINCT plein-scan côté navigateur.
        "filters": {
            "domaines": sorted({r["domaine"] for r in records if r["domaine"]}),
            "annees": sorted(annees, reverse=True),
        },
    }
