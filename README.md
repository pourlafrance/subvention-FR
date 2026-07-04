# Subventions FR — où va l'argent public&nbsp;?

Observatoire citoyen, **politiquement neutre**, des subventions publiques françaises.
Site statique alimenté **exclusivement** par des sources publiques officielles
(data.gouv.fr, INSEE, ASP, Commission européenne). Aucun backend.

> ⚠️ Le dépôt est livré avec un **jeu de données de démonstration** (fictif,
> clairement étiqueté par une bannière). Le pipeline réel prend le relais en CI
> une fois les sources validées — voir [ROADMAP.md](./ROADMAP.md).

## Principes

- **Sources officielles uniquement**, citées et datées.
- **Neutralité par conception** : les domaines (culture, écologie, social…) ne sont
  pas inventés mais dérivés de la **classification COFOG** (INSEE/ONU). Le site décrit, il ne commente pas.
- **Honnêteté sur les angles morts** : la part non documentée est affichée, pas masquée.
- **Garde-fous légaux** : aucune personne physique nommée (RGPD ; CJUE 2010 pour la PAC).
- **Fail-loud** : un run CI vert garantit de vraies données.

## Architecture

Deux artefacts produits au *build* par le pipeline, parce qu'ils ont des contraintes inverses :

- `public/data/stats.json` — agrégats précalculés (KPI, répartition par domaine), chargés
  directement par l'accueil.
- `public/data/subventions.json` / `subventions.db` — le détail. La couche d'accès
  (`src/data/source.js`) bascule automatiquement selon le volume (`stats.meta.detail`) :
  JSON en mémoire pour la démo, base SQLite interrogée par requêtes HTTP Range
  (`sql.js-httpvfs`) au volume réel — voir
  [`src/data/sqlite.adapter.md`](./src/data/sqlite.adapter.md).

```
pipeline/        ETL Python (fetch → normalise → enrichit SIRENE → classe COFOG → contrôle → agrège → SQLite)
  sources/       connecteurs : associations SCDL, jaune budgétaire, PAC (ASP), aides d'État, CORDIS
  mapping/       tables auditables : programme → COFOG → domaine, IPC INSEE, plafonds COFOG (Eurostat)
  enrich.py      enrichissement bénéficiaires via l'API Recherche d'entreprises (SIRENE)
  checks.py      contrôles de cohérence fail-loud (plafond de dépense par division COFOG)
src/             front Vue 3 (accueil, recherche/liste, fiche, méthodologie)
public/data/     artefacts de données (démo committée, réel généré en CI)
.github/         workflows : déploiement Pages + rafraîchissement des données
```

## Démarrage

```bash
npm install
npm run data:sample   # (re)génère les données de démonstration
npm run dev           # http://localhost:5173
```

Pipeline réel (réseau requis, plutôt en CI ; `SUBV_ENRICH=0` pour sauter
l'enrichissement SIRENE) :

```bash
pip install -r pipeline/requirements.txt
python -m pipeline.build
```

Les connecteurs sont validés sur les vraies données (voir ROADMAP, jalon D2),
mais au volume réel la couche détail dépasse le seuil JSON : la bascule SQLite
côté front (jalon P2) est le préalable au premier run réel publié.

## Déploiement et mise à jour automatique

Tout tourne sur GitHub, sans autre service :

1. Pousser sur `main` déclenche `.github/workflows/deploy.yml` (build + GitHub Pages).
   Activer Pages dans *Settings → Pages → Source : GitHub Actions*. Le routage par hash
   évite les 404 au rafraîchissement, quel que soit le nom du dépôt.
2. Chaque lundi, `data-refresh.yml` exécute le pipeline réel et publie les artefacts
   dans la release **`donnees-latest`** (la base SQLite n'est jamais committée), puis
   redéclenche le déploiement.
3. `deploy.yml` embarque les données de la release si elle existe, sinon la démo
   étiquetée. Premier run réel réussi → la bannière démo disparaît d'elle-même.

## Licence

Code sous licence MIT. Les données restent soumises aux licences de leurs producteurs
(Licence Ouverte / Etalab pour data.gouv.fr et l'ASP).
