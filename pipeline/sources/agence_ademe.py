"""Source : les aides financières de l'ADEME (opérateur de l'État).

Publiées au format « données essentielles » (SCDL subventions) sur le portail
data-fair de l'ADEME, référencées sur data.gouv.fr (dataset
640afdff7a07961cdc232d19). ~39 000 lignes, mise à jour quotidienne,
SIRET natif. Parseur validé sur fichier réel (2026-07-04) : délimiteur
virgule, UTF-8 BOM, dateConvention ISO.

PÉRIMÈTRE : personnes morales privées uniquement. Les SIREN commençant par
1 (État) ou 2 (collectivités territoriales) sont écartés — une aide d'un
opérateur de l'État à une commune est un transfert public-public, hors
objet du site (même règle que pour CORDIS). Écarts comptés, jamais silencieux.

Le type par défaut est « entreprise » (public majoritaire du dispositif) ;
l'enrichissement SIRENE requalifie les associations.
"""
from __future__ import annotations

import re

import requests

from . import common
from ..normalize import make_record, to_float, to_year

# API lines du portail data-fair (l'export /raw est un xlsx). Pagination par
# curseur : 10 000 lignes max par page, suivant le header « Link rel=next ».
LINES_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/les-aides-financieres-de-l%27ademe/lines"
DATASET_PAGE = "https://www.data.gouv.fr/fr/datasets/640afdff7a07961cdc232d19/"
SOURCE_NAME = "Aides financières de l'ADEME (data.ademe.fr)"


def _pages():
    url, params = LINES_URL, {"format": "csv", "size": 10_000}
    while url:
        r = requests.get(url, params=params, timeout=common.TIMEOUT)
        r.raise_for_status()
        yield r.text
        m = re.search(r"<([^>]+)>;\s*rel=next", r.headers.get("link", ""))
        url, params = (m.group(1), None) if m else (None, None)


def fetch() -> list[dict]:
    rows = [row for page in _pages() for row in common.read_csv(page)]
    records: list[dict] = []
    publics = 0
    for row in rows:
        nom = common.pick(row, "nomBeneficiaire")
        if not nom:
            continue
        siret = common.pick(row, "idBeneficiaire")
        siren = siret[:9] if siret[:9].isdigit() else ""
        if siren[:1] in ("1", "2"):  # État / collectivités : hors périmètre
            publics += 1
            continue
        rec = make_record(
            nom=nom,
            type_="entreprise",
            annee=to_year(common.pick(row, "dateConvention", "datesPeriodeVersement")),
            montant=to_float(common.pick(row, "montant")),
            objet=common.pick(row, "objet", "dispositifAide"),
            financeur_type="operateur",
            financeur_nom="ADEME",
            siren=siren,
            departement=common.pick(row, "_siret_infos._infos_commune.code_departement"),
            pays="FR",
            source=SOURCE_NAME,
            source_url=DATASET_PAGE,
            ref=common.pick(row, "referenceDecision") or siret,
        )
        rec["source_kind"] = "agence_ademe"
        records.append(rec)
    if not records:
        raise RuntimeError("ADEME : 0 enregistrement exploitable (format modifié ?).")
    print(f"::notice::ADEME : {publics} lignes vers des personnes publiques écartées (hors périmètre)")
    return records
