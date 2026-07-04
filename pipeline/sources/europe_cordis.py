"""Source : financements Horizon Europe aux entreprises françaises (CORDIS).

Export bulk officiel de la Commission européenne, rafraîchi ~mensuellement :
https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip (~33 Mo).
Le zip contient organization.csv (participations, contribution UE par
organisation, TVA intracommunautaire) et project.csv (dates, titres).
Référencé sur data.europa.eu (« CORDIS - EU research projects under Horizon
Europe »). Parseur validé sur l'export du 2026-06-16.

PÉRIMÈTRE : uniquement les personnes morales PRIVÉES françaises
(activityType == "PRC", sociétés). Les universités et organismes publics
participent aussi à Horizon, mais un versement UE à une entité publique
n'est pas une « subvention à un bénéficiaire » au sens de ce site.
Le SIREN est extrait du numéro de TVA intracommunautaire (FRxx + SIREN).

LIMITE ASSUMÉE : le montant est la contribution UE contractualisée sur toute
la durée du projet, rattachée à l'année de DÉBUT (CORDIS ne publie pas
d'échéancier de versements). Des années futures peuvent donc apparaître :
ce sont des engagements, pas des paiements.

Particularités du format : délimiteur « ; », encodage UTF-8 avec BOM,
décimales à virgule.
"""
from __future__ import annotations

import csv
import io
import os
import time
import zipfile

import requests

from ..normalize import dept_from_insee, make_record, to_float, to_year

ZIP_URL = "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip"
LOCAL_ZIP = os.path.join(os.path.dirname(__file__), "..", ".cache", "cordis-horizon.zip")
SOURCE_NAME = "Horizon Europe — CORDIS (Commission européenne)"
TIMEOUT = 300


def _get_zip() -> zipfile.ZipFile:
    """Télécharge l'export (ou réutilise le cache local hors CI).

    Reprises avec attente : un transfert de ~35 Mo peut être tronqué en vol
    (IncompleteRead constaté en CI) — un zip tronqué lève BadZipFile à
    l'ouverture, ce qui déclenche aussi la reprise.
    """
    if os.path.exists(LOCAL_ZIP) and not os.environ.get("CI"):
        return zipfile.ZipFile(LOCAL_ZIP)
    os.makedirs(os.path.dirname(LOCAL_ZIP), exist_ok=True)
    derniere_erreur = None
    for tentative in range(3):
        if tentative:
            time.sleep(20 * tentative)
        try:
            r = requests.get(ZIP_URL, timeout=TIMEOUT)
            r.raise_for_status()
            with open(LOCAL_ZIP, "wb") as f:
                f.write(r.content)
            return zipfile.ZipFile(LOCAL_ZIP)
        except (requests.RequestException, zipfile.BadZipFile) as exc:
            derniere_erreur = exc
            print(f"::warning::CORDIS : tentative {tentative + 1}/3 en échec ({exc})")
    raise RuntimeError(f"CORDIS : téléchargement en échec après 3 tentatives ({derniere_erreur})")


def _read(z: zipfile.ZipFile, name: str):
    return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"), delimiter=";")


def _siren_from_vat(vat: str) -> str:
    """TVA intracommunautaire française FR + 2 caractères de clé + SIREN."""
    vat = (vat or "").replace(" ", "").upper()
    if vat.startswith("FR") and len(vat) == 13 and vat[4:].isdigit():
        return vat[4:]
    return ""


def fetch() -> list[dict]:
    z = _get_zip()

    projets: dict[str, dict] = {}
    for row in _read(z, "project.csv"):
        projets[row["id"]] = {"annee": to_year(row.get("startDate")), "titre": row.get("title") or ""}
    if not projets:
        raise RuntimeError("CORDIS : project.csv vide ou illisible (format modifié ?).")

    records: list[dict] = []
    for row in _read(z, "organization.csv"):
        if row.get("country") != "FR" or row.get("activityType") != "PRC":
            continue
        montant = to_float(row.get("ecContribution"))
        if not montant or montant <= 0:
            continue
        proj = projets.get(row.get("projectID") or "")
        rec = make_record(
            nom=row.get("name") or "",
            type_="entreprise",
            annee=proj["annee"] if proj else None,
            montant=montant,
            objet=(proj["titre"] if proj else "") or "Projet Horizon Europe",
            financeur_type="ue",
            financeur_nom="Commission européenne — Horizon Europe",
            siren=_siren_from_vat(row.get("vatNumber")),
            commune=row.get("city") or "",
            departement=dept_from_insee(row.get("postCode")),
            pays="FR",
            source=SOURCE_NAME,
            source_url=ZIP_URL,
            ref=row.get("projectID") or "",
        )
        rec["source_kind"] = "ue_recherche"
        records.append(rec)

    if not records:
        raise RuntimeError("CORDIS : 0 entreprise française extraite (format modifié ?).")
    return records
