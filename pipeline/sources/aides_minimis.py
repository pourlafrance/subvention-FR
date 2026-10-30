"""Source : registre public national des aides de minimis.

Jeu `aides_minimis` de data.economie.gouv.fr (DGE), issu de la plateforme
Aides d'État prévue par la circulaire du 4 mars 2026. Aides octroyées depuis le
01/01/2026 (01/01/2027 pour l'agriculture). Le montant publié est l'équivalent
subvention brut : un prêt y compte pour son avantage, pas pour son capital.

PÉRIMÈTRE : personnes morales privées uniquement. Le registre n'indique pas la
forme juridique et environ un tiers des SIREN sont des entrepreneurs individuels
(échantillon de 200 SIREN, octobre 2026), donc des personnes physiques. Une ligne
n'est retenue que si sa fiche SIRENE confirme une personne morale privée : tout
SIREN non vérifié reste exclu jusqu'au run suivant. Les lignes de l'ADEME sont
écartées, déjà comptées par sa propre source. Écarts comptés, jamais silencieux.
"""
from __future__ import annotations

import re

from . import common
from ..enrich import fiches_sirene
from ..normalize import make_record, to_float, to_year

EXPORT_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/aides_minimis/exports/json"
DATASET_PAGE = "https://data.economie.gouv.fr/explore/dataset/aides_minimis/"
SOURCE_NAME = "Registre public des aides de minimis (data.economie.gouv.fr)"
MAX_LOOKUPS = 4000  # ~25 min d'appels par run ; le cache SIRENE complète le reste semaine après semaine
# Catégories juridiques INSEE : 5 sociétés, 6 autres formes commerciales ou
# coopératives, 8 organismes privés spécialisés, 9 associations et assimilés.
CATEGORIES_RETENUES = ("5", "6", "8", "9")


def _retenue(info: dict | None) -> bool:
    return bool(info) and (info.get("nature_juridique") or "").startswith(CATEGORIES_RETENUES)


def _sirens_par_volume(rows: list[dict]) -> list[str]:
    volume: dict[str, float] = {}
    for row in rows:
        siren = row["identifiant_beneficiaire"]
        volume[siren] = volume.get(siren, 0) + (row.get("montant_esb") or 0)
    return sorted(volume, key=lambda s: -volume[s])


def _record(row: dict) -> dict:
    rec = make_record(
        nom=row["nom_beneficiaire"],
        type_="entreprise",  # l'enrichissement SIRENE requalifie les associations
        annee=to_year(row.get("date_octroi")),
        montant=to_float(row.get("montant_esb")),
        objet=f"Aide de minimis ({row.get('instrument_aide') or 'instrument non précisé'})",
        # L'autorité peut être l'État ou une collectivité : non typé ici.
        financeur_type="",
        financeur_nom=row.get("autorite") or "",
        siren=row["identifiant_beneficiaire"],
        commune="" if row.get("commune_beneficiaire") == "-" else row.get("commune_beneficiaire") or "",
        pays="FR",
        source=SOURCE_NAME,
        source_url=DATASET_PAGE,
        ref=row.get("date_octroi") or "",
    )
    rec["source_kind"] = "aide_minimis"
    return rec


def fetch() -> list[dict]:
    rows = common.http_get(EXPORT_URL).json()
    if not rows:
        raise RuntimeError("De minimis : export vide (jeu déplacé ou format modifié ?).")

    utiles = []
    sans_siren = etrangers = ademe = 0
    for row in rows:
        if not re.fullmatch(r"\d{9}", row.get("identifiant_beneficiaire") or ""):
            sans_siren += 1
        elif row.get("pays_beneficiaire") != "France":
            etrangers += 1
        elif row.get("autorite") == "ADEME":
            ademe += 1
        else:
            utiles.append(row)

    fiches, s = fiches_sirene(_sirens_par_volume(utiles), MAX_LOOKUPS)
    records = []
    non_verifiees = hors_perimetre = 0
    for row in utiles:
        siren = row["identifiant_beneficiaire"]
        if siren not in fiches:
            non_verifiees += 1
        elif _retenue(fiches[siren]):
            records.append(_record(row))
        else:  # entrepreneur individuel, personne publique ou fiche introuvable
            hors_perimetre += 1

    if not records:
        raise RuntimeError("De minimis : aucune ligne retenue (SIRENE indisponible ?).")
    print(f"::notice::De minimis : {len(rows)} lignes, {len(records)} retenues, "
          f"{hors_perimetre} hors périmètre (personnes physiques, public), "
          f"{non_verifiees} en attente de vérification SIRENE, {ademe} déjà dans ADEME, "
          f"{sans_siren} sans SIREN, {etrangers} à l'étranger ; "
          f"{s['appels']} appels SIRENE, {s['erreurs']} erreurs")
    if s["arret_anticipe"]:
        print("::warning::De minimis : vérification SIRENE interrompue, API indisponible ?")
    return records
