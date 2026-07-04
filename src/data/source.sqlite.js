/*
 * Adaptateur SQLite — sql.js-httpvfs (jalon P2).
 *
 * Interroge public/data/subventions.db par requêtes HTTP Range : le navigateur
 * ne télécharge que les pages (1 Ko) de la base nécessaires à chaque requête.
 * Fonctionne sur tout hébergement statique servant les Range (GitHub Pages).
 *
 * Règles :
 *  - jamais de scan complet côté client : recherche via FTS5, listes via les
 *    index (domaine/annee/montant DESC), fiche par clé primaire ;
 *  - les agrégats (KPI, domaines, filtres) viennent de stats.json, précalculés
 *    en CI sur la TOTALITÉ des données — jamais recalculés ici ;
 *  - le seul comptage fait en ligne (total de résultats filtrés) est plafonné
 *    à COUNT_CAP et signalé comme tel (`totalCapped`) — il n'alimente aucun KPI.
 */
import { createDbWorker } from 'sql.js-httpvfs'
import workerUrl from 'sql.js-httpvfs/dist/sqlite.worker.js?url'
import wasmUrl from 'sql.js-httpvfs/dist/sql-wasm.wasm?url'

const COUNT_CAP = 10_000
const EXPORT_MAX = 5_000

function ftsQuery(text) {
  // Tokens alphanumériques, sans accents, en préfixe : `resto* coeur*`
  const tokens = (text || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .match(/[a-zA-Z0-9]+/g) || []
  return tokens.map((t) => `"${t}"*`).join(' ')
}

export async function createSqliteSource(BASE, stats) {
  const worker = await createDbWorker(
    [{
      from: 'inline',
      config: {
        serverMode: 'full',
        // URL absolue, résolue dans le contexte de la PAGE : le worker vit
        // sous /assets/ et résoudrait une URL relative depuis là (404).
        url: new URL(`${BASE}data/subventions.db`, window.location.href).toString(),
        requestChunkSize: 1024,
        // Taille exacte fournie par le pipeline : le gzip de GitHub Pages
        // fausse la détection par HEAD (voir sqlite.adapter.md).
        fileLength: stats?.meta?.db_bytes,
      },
    }],
    workerUrl,
    wasmUrl,
  )
  const q = (sql, params = []) => worker.db.query(sql, params)

  function buildWhere({ q: text = '', type = '', domaine = '', annee = '', etranger = false }) {
    const where = []
    const params = []
    const fts = ftsQuery(text)
    if (fts) {
      where.push('s.id IN (SELECT subvention_id FROM recherche WHERE recherche MATCH ?)')
      params.push(fts)
    }
    if (type) { where.push('b.type = ?'); params.push(type) }
    if (domaine) { where.push('s.domaine = ?'); params.push(domaine) }
    if (annee) { where.push('s.annee = ?'); params.push(Number(annee)) }
    if (etranger) where.push('b.est_etranger = 1')
    return { sql: where.length ? 'WHERE ' + where.join(' AND ') : '', params, filtered: where.length > 0 }
  }

  const SELECT = `
    SELECT s.id, s.annee, s.montant, s.objet, s.financeur_type, s.financeur_nom,
           s.programme, s.mission, s.cofog, s.domaine, s.source, s.source_url,
           b.id AS b_id, b.nom AS b_nom, b.type AS b_type, b.siren AS b_siren,
           b.commune AS b_commune, b.pays AS b_pays, b.est_etranger AS b_etranger
    FROM subvention s JOIN beneficiaire b ON b.id = s.beneficiaire_id`

  function toRecord(r) {
    return {
      id: r.id, annee: r.annee, montant: r.montant, objet: r.objet,
      financeur_type: r.financeur_type, financeur_nom: r.financeur_nom,
      programme: r.programme, mission: r.mission, cofog: r.cofog, domaine: r.domaine,
      source: r.source, source_url: r.source_url,
      beneficiaire: {
        id: r.b_id, nom: r.b_nom, type: r.b_type, siren: r.b_siren,
        commune: r.b_commune, pays: r.b_pays, est_etranger: !!r.b_etranger,
      },
    }
  }

  return {
    async getStats() {
      return stats
    },

    async getFilters() {
      return stats.filters || { domaines: [], annees: [] }
    },

    async search({ q: text = '', type = '', domaine = '', annee = '', etranger = false, page = 1, pageSize = 20 } = {}) {
      const { sql, params, filtered } = buildWhere({ q: text, type, domaine, annee, etranger })
      const rows = await q(
        `${SELECT} ${sql} ORDER BY s.montant DESC LIMIT ? OFFSET ?`,
        [...params, pageSize, (page - 1) * pageSize],
      )
      let total, totalCapped = false
      if (!filtered) {
        total = stats.meta.n_records // exact, précalculé sur tout
      } else {
        const [{ n }] = await q(
          `SELECT COUNT(*) AS n FROM (SELECT 1 FROM subvention s JOIN beneficiaire b ON b.id = s.beneficiaire_id ${sql} LIMIT ${COUNT_CAP + 1})`,
          params,
        )
        totalCapped = n > COUNT_CAP
        total = totalCapped ? COUNT_CAP : n
      }
      return { items: rows.map(toRecord), total, totalCapped, page, pageSize }
    },

    async searchAll(filters = {}) {
      const { sql, params } = buildWhere(filters)
      const rows = await q(`${SELECT} ${sql} ORDER BY s.montant DESC LIMIT ${EXPORT_MAX + 1}`, params)
      return rows.map(toRecord)
    },

    async getBeneficiaire(id) {
      const [b] = await q('SELECT * FROM beneficiaire WHERE id = ?', [id])
      if (!b) return null
      const beneficiaire = {
        id: b.id, nom: b.nom, type: b.type, siren: b.siren, rna: b.rna, naf: b.naf,
        commune: b.commune, pays: b.pays, est_etranger: !!b.est_etranger,
        activite: b.activite, effectifs: b.effectifs,
      }
      const subs = await q(
        'SELECT * FROM subvention WHERE beneficiaire_id = ? ORDER BY annee DESC, montant DESC',
        [id],
      )
      return {
        beneficiaire,
        subventions: subs.map((s) => ({ ...s, beneficiaire })),
        total: b.total_eur,
        premiere_annee: b.premiere_annee,
        n: b.n_subventions,
      }
    },
  }
}

export { EXPORT_MAX }
