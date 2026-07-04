# Roadmap — Subventions FR

État au moment de la livraison initiale. Légende : ✅ fait · 🟡 partiel · ⬜ à faire.

---

## Résumé

Le **squelette complet est fonctionnel** : site Vue statique, pipeline ETL Python,
classification COFOG, deux workflows CI/CD, et un jeu de données de démonstration qui
fait tourner toutes les fonctionnalités du cahier des charges de bout en bout.

Mise à jour 2026-07 : les **connecteurs réels sont validés sur les vraies données**
(D2 fait — SCDL, jaune budgétaire, PAC via portail ASP, CORDIS), l'enrichissement
SIRENE, les euros constants et les contrôles de cohérence sont en place. Le volume
réel mesuré (~600-750 k lignes/an) rend la **bascule SQLite (P2) bloquante** avant le
premier run réel : c'est LE chantier prioritaire, suivi de D1 (mapping COFOG complet)
et D3 (aides d'État TAM). Le site est **publiable tel quel** (avec sa bannière
« démonstration »).

---

## ✅ Fait

### Socle technique
- ✅ Projet Vue 3 + Vite, build de production validé (`npm run build`).
- ✅ Routage par hash (pas de 404 au rafraîchissement sur GitHub Pages, base portable).
- ✅ Workflow de déploiement GitHub Pages (`deploy.yml`).
- ✅ Workflow de rafraîchissement des données par cron, fail-loud (`data-refresh.yml`).
- ✅ Système de design sobre (charte État : bleu Marianne, chiffres tabulaires, responsive, focus clavier).

### Front (cahier des charges)
- ✅ **Fonction recherche** (texte sur nom + objet, insensible aux accents).
- ✅ **KPI** : nb associations + volume €, nb entreprises + volume €, volume annuel, volume hors France.
- ✅ **Clic sur un KPI → page liste filtrée** (via paramètres d'URL).
- ✅ **Répartition par domaine** (graphe Chart.js), barres cliquables → liste filtrée.
- ✅ **Pagination + recherche + filtres** (type, domaine, année, hors France) sur la liste.
- ✅ **Fiche bénéficiaire** : total reçu, « aidé depuis » (première année), SIREN, détail des subventions, sources.
- ✅ **Disclaimer** complet (page Méthodologie) : « même l'État ne maîtrise pas tout », sourcé Sénat 2025.
- ✅ Bannière permanente tant que les données sont de démonstration.
- ✅ **Graphe temporel** du volume annuel (euros courants/constants, clic → liste de l'année).
- ✅ **Top 10 bénéficiaires** sur l'accueil, **sparkline** par année sur la fiche.
- ✅ **Export CSV** des résultats filtrés ; effectifs SIRENE affichés sur la fiche.
- ✅ Méthodologie enrichie : périmètre COVID exclu, euros constants, co-financements, limites
  « engagements vs versements » (SCDL, CORDIS), règle d'exclusion des personnes physiques PAC.

### Pipeline & données
- ✅ Schéma canonique unique (`normalize.py`), identité bénéficiaire stable (SIREN > RNA > hash).
- ✅ Classification déterministe programme → COFOG → domaine (`classify.py`).
- ✅ Agrégation KPI + estimation part visible/estimée (`aggregate.py`).
- ✅ Construction SQLite indexée + FTS5, `page_size=1024`, prête pour httpvfs (`build_sqlite.py`).
- ✅ Connecteurs **validés sur données réelles** : associations SCDL (53 datasets), jaune budgétaire,
  PAC (API portail ASP), Horizon Europe (CORDIS) ; aides d'État TAM (ingestion semi-manuelle).
- ✅ Enrichissement SIRENE des bénéficiaires (`enrich.py`) : type validé, NAF, commune, effectifs.
- ✅ Euros constants : table IPC INSEE versionnée (`mapping/ipc_insee.csv`) + série déflatée dans stats.json.
- ✅ Contrôles de cohérence fail-loud (`checks.py`) : plafond par division COFOG (référence Eurostat
  versionnée) ; compteurs de recouvrement inter-sources dans stats.json.
- ✅ Générateur de données de démonstration étiquetées (`make_sample.py`).

### Neutralité & droit
- ✅ Table de mapping COFOG versionnée et commentée (`pipeline/mapping/`).
- ✅ Exclusion des personnes physiques par défaut (filtre PAC + schéma).
- ✅ Aucune tentative de relier subvention ↔ impôt, ni de « vote » nominatif (limites assumées et expliquées).

---

## 🔧 À faire

### Jalon D — Données réelles (priorité 1)
- ⬜ **D1** — Régénérer `programme_cofog_domaine.csv` sur la nomenclature de la **dernière LFI**
  (état B sur Légifrance / nomenclature data.gouv) au lieu du socle saisi de mémoire. Couvrir les ~134 programmes.
  Piste : le jaune budgétaire (voir D2) contient les codes de programme réellement utilisés.
- ✅ **D2** — Connecteurs validés sur fichiers réels (2026-07) :
  - *Associations SCDL* : pas de consolidation nationale (`consolidate: false` officiel) → énumération
    des ~53 datasets déclarant le schéma `scdl/subventions` ; parseur validé sur Ville de Lyon (6 359
    lignes, 100 %) et Ille-et-Vilaine (en-têtes déformés, 95 %). `montant` = total de convention,
    datation en cascade (dateConvention → période de versement → référence de décision).
  - *Jaune budgétaire* (nouveau connecteur) : versements État 2023 par bénéficiaire, avec code
    programme — 112 698 lignes valides, 11,77 Md€. Rotation de millésime annuelle à prévoir.
  - *PAC* : rien d'exploitable sur data.gouv → API MicroStrategy du portail de reporting ASP (session
    anonyme validée), 1,3 M lignes EF 2025. Personnes physiques exclues par liste de formes juridiques
    (conservateur). Rotation annuelle des identifiants de cube à prévoir.
  - *Horizon Europe / CORDIS* (nouveau connecteur) : export bulk officiel, 3 265 entreprises FR,
    2,13 Md€, SIREN extrait de la TVA intracommunautaire (98 %).
- ⬜ **D3** — Brancher les **aides d'État aux entreprises** : automatiser l'export TAM (Commission
  européenne) et intégrer le futur **registre national « Aides d'État »** (circulaire du 4 mars 2026).
- ⬜ **D4** — Premier run réel de `data-refresh.yml` → publication de la release `donnees-latest`,
  redéploiement automatique, la bannière démo disparaît. **Débloqué** (P2 fait) — il reste à lancer
  le run et à surveiller durée/mémoire du job (PAC = 1,3 M lignes).
- ⬜ **D5** — **Kohesio** (FEDER/FSE+) : API REST validée (France = entité `Q20`, 63 304 projets,
  19 585 bénéficiaires agrégés). Le CSV national `FR-pp21-27-latest.csv` via `/api/data/object` est
  toujours en panne (retesté 2026-07-04 : 504 systématique, même sur les petits fichiers — panne du
  backend de stockage, pas un problème de taille). Repli possible mais coûteux : pagination
  `/api/projects` + hydratation détail par projet (~63 k appels ; les bénéficiaires n'apparaissent que
  dans le détail). Pas de SIREN nulle part → rapprochement par nom. Retester le bulk périodiquement ;
  parseur à valider sur le CSV réel dès l'endpoint rétabli.
- ✅ **D8** — **ADEME** : connecteur validé en direct (28 570 aides privées, 8,1 Md€ 2021-2026,
  SIREN 99 %, API data-fair paginée par curseur). Transferts public-public écartés et comptés
  (10 436). FranceAgriMer : rien d'exploitable par bénéficiaire sur data.gouv (vérifié) ; agences de
  l'eau : pas de CSV direct, portails propres à explorer.
- ⬜ **D6** — Automatiser la **rotation annuelle** des sources à millésime (cube PAC, jaune budgétaire) :
  découverte des identifiants au lieu de constantes en dur.
- ⬜ **D7** — Traîne SCDL (audit du 1er run réel, 2026-07) : 36/53 jeux lus. Restent ~5 publiants
  xlsx sans CSV (lecteur openpyxl à ajouter), 4 liens morts Grand Lyon (à signaler au publiant),
  et quelques jeux hors-schéma malgré leur déclaration. Couverture annotée à chaque run.
  Constaté aussi : la couverture VARIE d'un run à l'autre (38 224 à 54 173 lignes selon la
  disponibilité des hôtes des collectivités) → prévoir un cache « dernière version saine » par
  jeu de données pour lisser les pannes passagères.

### Jalon P — Passage à l'échelle (le volume réel est maintenant MESURÉ)
- ✅ **P1** — Volume réel mesuré (D2) : PAC ~530 k lignes morales/exercice + jaune ~113 k + SCDL
  ~50-100 k + CORDIS ~3 k ≈ **600-750 k lignes/an** → le JSON de détail est disqualifié, `build.py`
  ne l'écrira pas (> 50 000). L'accueil (stats.json) reste fonctionnel.
- ✅ **P2** — `src/data/source.sqlite.js` (sql.js-httpvfs) : recherche FTS5, pagination indexée,
  fiche par clé, bascule automatique via `stats.meta.detail`. Validé en navigateur headless derrière
  un serveur Range réel (voir [`src/data/sqlite.adapter.md`](./src/data/sqlite.adapter.md)).
  Comptages en ligne plafonnés et signalés (« 10 000+ ») — les KPI restent précalculés en CI sur tout.
- ✅ **P3** — Résolu après diagnostic sur le premier déploiement réel : la CDN de Pages sert les
  Range dans l'espace gzip (inexploitables en partiel) → base découpée en chunks de 1 Mo
  (`split_db.py`) requêtés en fichiers entiers, cacheBust par version, `db_bytes` explicite.
  Détail complet dans [`src/data/sqlite.adapter.md`](./src/data/sqlite.adapter.md).

### Jalon F — Fonctionnalités
- ⬜ **F1** — Estimation « petits budgets » plus fine et mieux sourcée (actuellement ratio macro grossier) ;
  l'afficher comme un KPI à part entière « part visible vs estimée » avec méthode détaillée.
- ✅ **F2** — Série temporelle du volume annuel en graphe (cliquable → liste de l'année), en euros
  courants ET constants (table IPC INSEE versionnée dans `mapping/ipc_insee.csv`, idbank 001764363).
- 🟡 **F3** — Subventions des **collectivités** : couvertes de fait par le connecteur SCDL (les ~53
  publiants sont majoritairement des collectivités). Reste : afficher le taux de couverture territorial.
- ✅ **F4** — Enrichissement SIRENE (`pipeline/enrich.py`, API Recherche d'entreprises) : validation du
  type de bénéficiaire (le drapeau `est_association` fait foi), NAF, commune, effectifs, état
  administratif. Cache inter-runs (CI : actions/cache). Testé en direct dans les deux sens.
- ✅ **F5** — Export CSV des résultats filtrés (bouton sur la liste) ; lien profond déjà permis par l'URL.
- ⬜ **F6** — Affiner la nationalité « hors France » (aujourd'hui : pays d'enregistrement ; le capital reste hors de portée).
- ✅ **F7** — Top 10 bénéficiaires sur l'accueil (`top_beneficiaires` dans stats.json).
- ✅ **F8** — Sparkline des montants par année sur la fiche bénéficiaire (SVG, sans dépendance).

### Jalon Q — Qualité & gouvernance
- 🟡 **Q1** — Annotations de diagnostic enrichies : compteurs par source, par jeu SCDL, enrichissement
  SIRENE, recouvrement inter-sources (`meta.recouvrement` dans stats.json). Reste : les afficher sur le site.
- ⬜ **Q2** — Page publique listant la table COFOG + procédure de contestation (issue GitHub) d'une ligne.
- 🟡 **Q3** — Contrôle croisé fait côté plafond : `pipeline/checks.py` échoue si un total par division
  COFOG dépasse la dépense APU totale (référence Eurostat `gov_10a_exp` versionnée dans
  `mapping/controle_cofog_apu.csv`), testé pass/fail. Reste : figer des fichiers réels d'échantillon
  comme tests de non-régression des parseurs.
- ⬜ **Q4** — Accessibilité (audit lecteur d'écran) et performance (lazy-load du graphe).

---

## Risques & décisions ouvertes

- **Complétude vs crédibilité** : le risque n°1 identifié par Data.Subvention est qu'« incomplet » soit lu comme
  « faux ». Réponse : afficher partout les taux de couverture, jamais un total qui se présente comme exhaustif.
- **Stabilité de la nomenclature** : les libellés de programmes changent chaque année — on **clé sur le code numérique**.
- **Cinéma / artistes** : flux en partie *opérateur* (CNC, taxes affectées), pas *programme* → isolable seulement
  là où l'objet/opérateur le nomme. À documenter dans la méthodo.
- **TAM** : pas d'API ouverte commode → ingestion semi-manuelle au départ (D3).

---

## Cahier des charges → état

| Demande | État |
|---|---|
| Fonction recherche | ✅ |
| KPI nb associations + volume € | ✅ |
| KPI nb entreprises + volume € | ✅ |
| Volume € annuel | ✅ (KPI + graphe temporel cliquable, euros courants et constants) |
| Répartition par domaine (État) | ✅ |
| Estimation incluant petits budgets | 🟡 (ratio macro ; à affiner → F1) |
| Disclaimer « l'État ne maîtrise pas tout » | ✅ |
| Volume attribué à l'étranger | 🟡 (pays d'enregistrement ; capital hors portée → F6) |
| Clic KPI → page détail liée | ✅ |
| Pagination + recherche sur les listes | ✅ |
| Fiche détaillée (objet, depuis quand, etc.) | ✅ |
| Qui a voté | ⬜ Hors portée (autorité versante affichée ; voir Méthodologie) |
| Lien subvention ↔ taxe | ⬜ Impossible (universalité budgétaire ; rattachement au programme à la place) |
