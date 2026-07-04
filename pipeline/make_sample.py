"""Génère un jeu de données de DÉMONSTRATION (is_sample=true).

Objectif : permettre au site de fonctionner avant que le pipeline réel n'ait
tourné en CI, SANS jamais faire passer du factice pour du sourcé. Les noms de
bénéficiaires sont volontairement fictifs et le site affiche une bannière
d'avertissement tant que is_sample vaut true.

    python -m pipeline.make_sample
"""
from __future__ import annotations

import json
import os
import random

from .aggregate import build_stats
from .classify import classify_all, load_mapping
from .normalize import make_record
from .build_sqlite import build as build_sqlite
from .split_db import split as split_db

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "public", "data")
random.seed(42)

# Programmes présents dans la table de mapping, pour des domaines cohérents.
PROGRAMMES = ["131", "175", "334", "180", "219", "163", "174", "113", "140",
              "150", "172", "304", "157", "177", "204", "102", "134"]
MISSIONS = {
    "131": "Culture", "175": "Culture", "334": "Médias livre et industries culturelles",
    "180": "Médias livre et industries culturelles", "219": "Sport jeunesse et vie associative",
    "163": "Sport jeunesse et vie associative", "174": "Écologie", "113": "Écologie",
    "140": "Enseignement scolaire", "150": "Recherche et enseignement supérieur",
    "172": "Recherche et enseignement supérieur", "304": "Solidarité",
    "157": "Solidarité", "177": "Cohésion des territoires", "204": "Santé",
    "102": "Travail et emploi", "134": "Économie",
}
OBJETS = [
    "Fonctionnement annuel de la structure", "Projet d'action culturelle",
    "Soutien à un programme de recherche", "Action d'insertion par l'emploi",
    "Festival et diffusion artistique", "Accompagnement de publics fragiles",
    "Rénovation et équipement", "Programme éducatif territorial",
]
COMMUNES = ["Paris", "Lyon", "Marseille", "Lille", "Bordeaux", "Nantes", "Strasbourg", "Rennes"]
DEPARTEMENTS = {"Paris": "75", "Lyon": "69", "Marseille": "13", "Lille": "59",
                "Bordeaux": "33", "Nantes": "44", "Strasbourg": "67", "Rennes": "35"}


def gen_records(n_assos=45, n_ents=25):
    records = []
    for i in range(n_assos):
        prog = random.choice(PROGRAMMES)
        nom = f"Association Démonstration {chr(65 + i % 26)}{i:02d}"
        base = random.choice([8_000, 15_000, 40_000, 120_000, 300_000])
        for annee in range(2018 + random.randint(0, 3), 2025):
            records.append(make_record(
                nom=nom, type_="association", annee=annee,
                montant=round(base * random.uniform(0.7, 1.3), -2),
                objet=random.choice(OBJETS), financeur_type="etat",
                financeur_nom="Ministère (démonstration)", programme=prog,
                mission=MISSIONS[prog], siren=f"{100000000 + i}", naf="9499Z",
                commune=(commune := random.choice(COMMUNES)),
                departement=DEPARTEMENTS[commune], pays="FR",
                source="DÉMONSTRATION", source_url="#demo",
            ) | {"source_kind": "association"})
    for i in range(n_ents):
        nom = f"Entreprise Exemple {chr(65 + i % 26)}{i:02d}"
        etranger = i % 9 == 0
        base = random.choice([600_000, 1_200_000, 3_000_000, 8_000_000])
        for annee in range(2019 + random.randint(0, 3), 2025):
            records.append(make_record(
                nom=nom, type_="entreprise", annee=annee,
                montant=round(base * random.uniform(0.6, 1.4), -3),
                objet="Aide à l'investissement (démonstration)", financeur_type="etat",
                financeur_nom="État (démonstration)", programme="134",
                mission="Économie", siren=f"{200000000 + i}", naf="2222Z",
                commune=(commune := random.choice(COMMUNES)),
                departement=DEPARTEMENTS[commune],
                pays="DE" if etranger else "FR",
                source="DÉMONSTRATION", source_url="#demo",
            ) | {"source_kind": "aide_etat_entreprise"})
    return records


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    records = classify_all(gen_records(), load_mapping())
    info = build_sqlite(records, os.path.join(OUT_DIR, "subventions.db"))
    split_db(os.path.join(OUT_DIR, "subventions.db"))  # chunks pour le mode SQLite
    stats = build_stats(records, is_sample=True, sources=[{"nom": "DONNÉES DE DÉMONSTRATION", "n": len(records)}])
    stats["meta"]["detail"] = "json"  # la démo reste servie en JSON
    stats["meta"]["db_bytes"] = info["bytes"]
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT_DIR, "subventions.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Démo générée : {len(records)} subventions, {info['beneficiaires']} bénéficiaires, "
          f"{round(info['bytes']/1e6, 2)} Mo")


if __name__ == "__main__":
    main()
