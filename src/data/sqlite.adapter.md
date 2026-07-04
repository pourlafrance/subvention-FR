# Adaptateur SQLite (sql.js-httpvfs) — IMPLÉMENTÉ (jalon P2)

`source.sqlite.js` interroge `public/data/subventions.db` par requêtes HTTP
Range (pages de 1 Ko) via sql.js-httpvfs. La façade `source.js` choisit
l'implémentation selon `stats.meta.detail` écrit par le pipeline :
`"json"` (démo, ≤ 50 000 lignes) ou `"sqlite"` (volume réel).

## Contrats respectés

- Mêmes méthodes publiques que l'implémentation JSON : `getStats`,
  `getFilters`, `search`, `searchAll`, `getBeneficiaire`.
- **Aucune agrégation côté navigateur** : KPI, domaines et valeurs de filtres
  viennent de `stats.json`, précalculés en CI sur la totalité des données.
- Requêtes indexées uniquement : FTS5 (`recherche MATCH`, préfixes, accents
  retirés), tri par `idx_sub_montant`, filtres par `idx_sub_domaine` /
  `idx_sub_annee`, fiche par clé primaire.
- Le comptage de résultats filtrés est plafonné à 10 000 (`totalCapped`,
  affiché « 10 000+ ») ; l'export CSV à 5 000 lignes avec avertissement.
  Ces plafonds ne touchent jamais les KPI.

## Pièges GitHub Pages (traités — appris sur le premier déploiement réel)

- **La CDN de Pages sert les Range dans l'espace des octets COMPRESSÉS**
  (constaté 2026-07 : tout est gzippé, `Content-Range …/<taille gzip>`, corps
  = tranche du flux gzip). Les navigateurs envoyant toujours
  `Accept-Encoding: gzip`, les Range partiels sont inexploitables
  (« database disk image is malformed »). MAIS une plage couvrant tout le
  fichier renvoie le flux gzip complet, décodé correctement. D'où la parade :
  la base est **découpée en fichiers de 1 Mo** (`pipeline/split_db.py`, au
  déploiement) et le worker est configuré en mode chunké avec
  `requestChunkSize == serverChunkSize` — chaque requête couvre exactement un
  fichier. Validé contre un simulateur reproduisant ce comportement.
- **cacheBust par version des données** : sans lui, la CDN pourrait mélanger
  des chunks de deux runs différents (corruption silencieuse).
- **databaseLengthBytes explicite** : le pipeline écrit `meta.db_bytes` dans
  stats.json (le HEAD renvoie la taille compressée, inutilisable).
- **URL absolue** : l'URL des chunks est résolue dans le contexte de la page
  (`new URL(..., location.href)`) — le worker vit sous `/assets/` et casserait
  une URL relative.
- `page_size = 1024` appliqué par `build_sqlite.py`.
- La base n'est **pas committée** : publiée en release `donnees-latest` par
  `data-refresh.yml`, téléchargée puis découpée au build par `deploy.yml`
  (limite git 100 Mo contournée, historique préservé).

## Tester en local

```bash
npm run build
# servir dist/ avec un serveur gérant les Range, puis :
# http://localhost:PORT/?data=sqlite#/liste   (forçage du mode)
```
