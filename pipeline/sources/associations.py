"""Source : données essentielles des conventions de subvention (SCDL).

Format normalisé par l'arrêté du 17 novembre 2017 (décret n° 2017-779),
schéma officiel « scdl/subventions » (v2.1.1) sur schema.data.gouv.fr.

IL N'EXISTE PAS de consolidation nationale sur data.gouv.fr (vérifié 2026-07 :
`consolidate: false` dans la config officielle de schema.data.gouv.fr). La
voie réelle est d'énumérer les jeux de données qui DÉCLARENT ce schéma
(~53 publications : collectivités, quelques services de l'État) via
l'API : /api/2/datasets/?schema=scdl/subventions

Points validés sur fichiers réels (Ville de Lyon, Ille-et-Vilaine, 2026-07) :
  - `montant` = montant TOTAL de la convention (pluriannuelle le cas échéant),
    daté par `dateConvention`. Les fichiers ne portent pas d'échéancier chiffré
    des versements -> on assume ce grain « engagement », documenté dans la
    méthodo (même limite que CORDIS).
  - `idBeneficiaire` = SIRET (14 chiffres) -> SIREN = 9 premiers.
  - `rnaBeneficiaire` optionnel et souvent absent.
  - En-têtes et délimiteurs hétérogènes (virgule/point-virgule, accents,
    espaces) -> normalisation via common.pick / read_csv.

Le type par défaut est « association » (objet du canal données essentielles) ;
l'enrichissement SIRENE aval requalifie les entreprises le cas échéant.

Robustesse : une ressource morte chez UNE collectivité ne doit pas masquer
les 52 autres — les échecs par ressource sont comptés et affichés, et le run
échoue si plus de 20 % des jeux de données sont inexploitables (ou zéro
enregistrement au total). Aucun échec n'est silencieux.
"""
from __future__ import annotations

from . import common
from ..normalize import make_record, to_float, to_year

SCHEMA_ID = "scdl/subventions"
LIST_URL = "https://www.data.gouv.fr/api/2/datasets/"
SOURCE_NAME = "Données essentielles des subventions (SCDL, data.gouv.fr)"
MAX_ECHEC_RATIO = 0.2


def _datasets_scdl() -> list[dict]:
    """Tous les jeux de données déclarant le schéma scdl/subventions."""
    out, url, params = [], LIST_URL, {"schema": SCHEMA_ID, "page_size": 100}
    while url:
        data = common.http_get(url, params=params).json()
        out.extend(data.get("data", []))
        url, params = data.get("next_page"), None
    return out


def fetch() -> list[dict]:
    datasets = _datasets_scdl()
    if not datasets:
        raise RuntimeError(
            f"Aucun jeu de données ne déclare le schéma '{SCHEMA_ID}' — "
            "l'API data.gouv a probablement changé."
        )

    records: list[dict] = []
    echecs: list[str] = []
    for ds in datasets:
        try:
            resources = common.datagouv_csv_resources(ds["id"])
            n_avant = len(records)
            for res in resources:
                text = common.http_get(res["url"]).text
                for row in common.read_csv(text):
                    rec = _map_row(row, res["url"])
                    if rec:
                        rec["source_kind"] = "association"
                        records.append(rec)
            if len(records) == n_avant:
                raise RuntimeError("0 ligne exploitable")
        except Exception as exc:
            echecs.append(f"{ds.get('slug', ds['id'])} ({exc})")

    for e in echecs:
        print(f"::warning::SCDL — jeu de données inexploitable : {e}")
    if len(echecs) > MAX_ECHEC_RATIO * len(datasets):
        raise RuntimeError(
            f"SCDL : {len(echecs)}/{len(datasets)} jeux de données en échec "
            f"(seuil {int(MAX_ECHEC_RATIO * 100)} %)."
        )
    if not records:
        raise RuntimeError("Données essentielles : 0 enregistrement exploitable extrait.")
    print(f"::notice::SCDL : {len(datasets) - len(echecs)}/{len(datasets)} jeux de données lus")
    return records


def _map_row(row: dict, url: str) -> dict | None:
    nom = common.pick(row, "nomBeneficiaire", "beneficiaire", "nom_beneficiaire", "denomination")
    if not nom:
        return None
    siret = common.pick(row, "idBeneficiaire", "siret", "siren")
    siren = siret[:9] if siret[:9].isdigit() else ""
    # Datation en cascade : dateConvention (requise au schéma mais vide sur des
    # milliers de lignes réelles, ex. Ville de Lyon), puis période de versement,
    # puis référence de décision (souvent préfixée de l'année).
    annee = to_year(common.pick(row, "dateConvention", "annee", "date_convention", "dateDecision"))
    if annee is None:
        annee = to_year(common.pick(row, "datesPeriodeVersement"))
    if annee is None:
        annee = to_year(common.pick(row, "referenceDecision"))
    return make_record(
        nom=nom,
        type_="association",
        annee=annee,
        montant=to_float(common.pick(row, "montant", "montantTotal", "montant_total")),
        objet=common.pick(row, "objet", "objetSubvention"),
        # L'attribuant peut être l'État ou une collectivité : non typé ici.
        financeur_type="",
        financeur_nom=common.pick(row, "nomAttribuant", "attribuant", "nom_attribuant"),
        programme=common.pick(row, "programme", "codeProgramme", "programme_code"),
        mission=common.pick(row, "mission"),
        siren=siren,
        rna=common.pick(row, "rnaBeneficiaire", "rna", "idRna"),
        naf=common.pick(row, "naf", "ape"),
        commune=common.pick(row, "commune", "ville"),
        pays="FR",
        source=SOURCE_NAME,
        source_url=url,
    )
