"""Source : « jaune budgétaire » — Effort financier de l'État en faveur des
associations (annexe au PLF).

Publié chaque année par les ministères économiques et financiers sur
data.gouv.fr (un dataset par PLF). Contient les VERSEMENTS de l'État par
bénéficiaire, avec le code du programme budgétaire — ce qui alimente
directement la classification COFOG.

Millésime câblé : PLF 2025 (versements de l'exercice 2023), dataset
data.gouv `67884ef83b74bb8c78133b6d`, ressource CSV validée sur fichier réel
(188 304 lignes, point-virgule, UTF-8 BOM, 2026-07).
ROTATION ANNUELLE : pointer le dataset du PLF suivant quand il paraît
(rechercher « jaune effort financier associations » sur data.gouv.fr) et
ajuster ANNEE_VERSEMENTS.

Pièges constatés sur le fichier réel : espaces insécables dans les champs
texte, SIREN non numériques (« NR\nCHORUS » multi-lignes), colonnes datées
(« Objet 2023 », « Convention 2022 ») dont le nom change à chaque millésime.
"""
from __future__ import annotations

from . import common
from ..normalize import dept_from_insee, make_record, to_float

RESOURCE_URL = "https://www.data.gouv.fr/fr/datasets/r/9527d4a9-6e81-4109-913e-830f8d5b5c86"
DATASET_PAGE = "https://www.data.gouv.fr/fr/datasets/67884ef83b74bb8c78133b6d/"
SOURCE_NAME = "Jaune budgétaire associations — PLF 2025 (data.gouv.fr)"
ANNEE_VERSEMENTS = 2023  # exercice couvert par ce millésime


def _pick_prefixe(row: dict, prefixe: str) -> str:
    """Valeur de la première colonne dont le nom commence par `prefixe`
    (les colonnes du jaune sont suffixées de l'année : « Objet 2023 »…)."""
    for k, v in row.items():
        if k and common._norm_key(k).startswith(common._norm_key(prefixe)) and v:
            return v
    return ""


def _type_depuis_cj(cj: str) -> str:
    """La catégorie juridique INSEE est fournie : 92xx = association,
    5xxx = société. Le jaune vise les associations mais contient des
    exceptions — on suit la catégorie plutôt que l'intitulé de l'annexe."""
    cj = (cj or "").strip()
    if cj.startswith("5"):
        return "entreprise"
    return "association"


def fetch() -> list[dict]:
    text = common.http_get(RESOURCE_URL).text
    records: list[dict] = []
    for row in common.read_csv(text):
        nom = common.pick(row, "Dénomination", "denomination")
        if not nom:
            continue
        siren = "".join(c for c in common.pick(row, "SIREN") if c.isdigit())
        rec = make_record(
            nom=nom,
            type_=_type_depuis_cj(common.pick(row, "Catégorie juridique")),
            annee=ANNEE_VERSEMENTS,
            montant=to_float(common.pick(row, "Montant")),
            objet=_pick_prefixe(row, "Objet"),
            financeur_type="etat",
            financeur_nom="État (jaune budgétaire)",
            programme=common.pick(row, "Programme"),
            siren=siren if len(siren) == 9 else "",
            commune=common.pick(row, "COG : libellé", "cog libelle"),
            departement=dept_from_insee(common.pick(row, "COG : code")),
            pays="FR",
            source=SOURCE_NAME,
            source_url=DATASET_PAGE,
            # NIC : distingue deux établissements d'un même SIREN recevant un
            # versement identique (cause du doublon d'id au premier run réel).
            ref=common.pick(row, "NIC"),
        )
        rec["source_kind"] = "jaune_associations"
        records.append(rec)
    if not records:
        raise RuntimeError("Jaune budgétaire : 0 enregistrement extrait (millésime à re-pointer ?).")
    return records
