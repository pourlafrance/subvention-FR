# Subventions FR — où va l'argent public&nbsp;?

**https://pourlafrance.github.io/subvention-FR/**

Observatoire citoyen, **politiquement neutre**, des subventions publiques
françaises&nbsp;: qui reçoit de l'argent public, combien, de qui, pour quoi.
Alimenté exclusivement par des données publiques officielles. Aucun backend,
aucun compte, aucun traceur&nbsp;: un site statique que chacun peut auditer.

## Le principe

L'argent public versé aux associations, aux entreprises et aux exploitations
agricoles est public… mais dispersé dans des dizaines de publications
(data.gouv.fr, ASP, Commission européenne, annexes budgétaires), dans des
formats hétérogènes et sans vue d'ensemble. Ce projet les consolide en un site
unique où chacun peut&nbsp;:

- **rechercher un bénéficiaire** et voir tout ce qu'il a reçu, depuis quand,
  versé par qui et à quel titre&nbsp;;
- voir la **répartition par domaine** (culture, écologie, social…) et
  l'**évolution du volume annuel**, en euros courants et constants&nbsp;;
- **exporter les résultats** (CSV) et vérifier chaque ligne à sa source.

## Neutralité par conception

- **Sources officielles uniquement**, citées et datées sur chaque ligne.
- **Aucune catégorie inventée**&nbsp;: les domaines dérivent de la
  classification internationale COFOG (ONU/OCDE, utilisée par l'INSEE)&nbsp;;
  la table de correspondance est versionnée dans ce dépôt et contestable.
- **Le site décrit, il ne commente pas**&nbsp;: aucun jugement n'est porté sur
  l'opportunité d'une subvention.
- **Honnêteté sur les angles morts**&nbsp;: la part non documentée est
  affichée, jamais masquée&nbsp;; les comptages partiels sont signalés comme
  tels&nbsp;; un contrôle automatique bloque toute publication incohérente
  avec les comptes nationaux.
- **Garde-fous légaux**&nbsp;: aucune personne physique nommée (RGPD&nbsp;;
  CJUE 2010 pour la PAC)&nbsp;; pas de lien subvention ↔ impôt (principe
  d'universalité budgétaire)&nbsp;; pas de vote nominatif par subvention.

## Sources consolidées

| Source officielle | Contenu |
|---|---|
| Données essentielles des subventions (SCDL, data.gouv.fr) | conventions des collectivités et services de l'État |
| Jaune budgétaire (annexe au PLF) | versements de l'État aux associations, par programme budgétaire |
| ASP | bénéficiaires de la PAC (FEAGA/FEADER), personnes morales uniquement |
| Commission européenne — TAM | aides d'État aux entreprises > 500 000 € |
| Commission européenne — CORDIS | financements Horizon Europe aux entreprises françaises |
| ADEME (data.ademe.fr) | aides à la transition écologique, personnes morales privées |
| INSEE — SIRENE | validation et enrichissement des fiches bénéficiaires |

Méthode, périmètre et limites assumées&nbsp;: page **Méthodologie** du site,
et [ROADMAP.md](./ROADMAP.md) pour l'état d'avancement.

## Fonctionnement

Un pipeline ouvert (`pipeline/`, Python) collecte, normalise, classe et agrège
les données chaque semaine en intégration continue, puis publie les artefacts.
Le site (`src/`, Vue 3) les interroge directement dans le navigateur — aucune
donnée ne transite par un serveur tiers. Tant que le pipeline réel n'a pas
alimenté la base, le site affiche un jeu de démonstration clairement étiqueté
par une bannière permanente.

Développement local&nbsp;: `npm install && npm run dev`.

## Contester une donnée, contribuer

Une ligne douteuse, une classification contestable, une source manquante&nbsp;?
Ouvrez une **issue GitHub** avec le lien de la fiche concernée. Les connecteurs
de sources, les tables de correspondance et les contrôles de cohérence sont
dans `pipeline/`&nbsp;: tout est auditable et chaque correction est tracée.

## Licence

Code sous licence MIT. Les données restent soumises aux licences de leurs
producteurs (Licence Ouverte / Etalab pour data.gouv.fr et l'ASP, conditions
propres aux portails de la Commission européenne).
