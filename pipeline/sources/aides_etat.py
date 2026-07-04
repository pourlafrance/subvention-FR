"""Source : aides d'État aux entreprises (> 500 000 €).

Portail Transparency Award Module (TAM) de la Commission européenne. L'export
n'est pas une API ouverte commode : on ingère un CSV exporté depuis le portail
et déposé dans pipeline/.cache/tam.csv (ou une URL configurée).

À VALIDER (ROADMAP D3) : automatiser l'export TAM, et intégrer le futur registre
national « Aides d'État » (circulaire du 4 mars 2026) pour les aides de minimis.
"""
from __future__ import annotations

import os

from . import common
from ..normalize import make_record, to_float, to_year

SOURCE_NAME = "Aides d'État > 500 k€ — Commission européenne (TAM)"
LOCAL_CSV = os.path.join(os.path.dirname(__file__), "..", ".cache", "tam.csv")


def fetch() -> list[dict]:
    if not os.path.exists(LOCAL_CSV):
        # Source semi-manuelle : absence non bloquante pour le reste du pipeline.
        print(f"::notice::TAM ignoré (aucun export trouvé en {LOCAL_CSV})")
        return []
    with open(LOCAL_CSV, encoding="utf-8") as f:
        text = f.read()
    records = []
    for row in common.read_csv(text):
        nom = common.pick(row, "Beneficiary name", "beneficiaire", "nom")
        if not nom:
            continue
        pays = common.pick(row, "Country", "pays", "region_pays") or "FR"
        rec = make_record(
            nom=nom,
            type_="entreprise",
            annee=to_year(common.pick(row, "Date granted", "annee", "date")),
            montant=to_float(common.pick(row, "Aid amount", "montant", "nominal_amount")),
            objet=common.pick(row, "Objective", "objet", "instrument"),
            financeur_type="etat",
            financeur_nom=common.pick(row, "Granting authority", "autorite") or "État",
            naf=common.pick(row, "Sector", "naf"),
            pays=pays[:2].upper() if len(pays) >= 2 else "FR",
            source=SOURCE_NAME,
            source_url="https://webgate.ec.europa.eu/competition/transparency/public/",
        )
        rec["source_kind"] = "aide_etat_entreprise"
        records.append(rec)
    return records
