/*
 * Couche d'accès aux données — façade.
 *
 * Deux implémentations, choisies automatiquement selon ce que le pipeline a
 * produit (stats.json -> meta.detail) :
 *   - "json"   : public/data/subventions.json chargé en mémoire (démo et
 *                petits volumes, <= 50 000 lignes) ;
 *   - "sqlite" : public/data/subventions.db interrogée par requêtes HTTP Range
 *                via sql.js-httpvfs (volume réel) — voir source.sqlite.js.
 *
 * Forçage manuel pour tester : ajouter ?data=sqlite (ou ?data=json) à l'URL,
 * avant le hash — ex. http://localhost:5173/?data=sqlite#/liste
 *
 * Dans les deux modes, les KPI et agrégats viennent de stats.json, précalculés
 * en CI sur la totalité des données : le navigateur n'agrège jamais.
 */

const BASE = import.meta.env.BASE_URL

function deburr(s) {
  return (s || '').toString().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

/* ---------- Implémentation JSON (démo / petits volumes) ---------- */

async function createJsonSource(stats) {
  const records = await fetch(`${BASE}data/subventions.json`).then((r) => (r.ok ? r.json() : []))
  records.forEach((r) => {
    r._search = deburr(r.beneficiaire?.nom) + ' ' + deburr(r.objet)
  })

  function applyFilters({ q = '', type = '', domaine = '', annee = '', etranger = false } = {}) {
    const nq = deburr(q.trim())
    const items = records.filter((r) => {
      if (type && r.beneficiaire?.type !== type) return false
      if (domaine && r.domaine !== domaine) return false
      if (annee && String(r.annee) !== String(annee)) return false
      if (etranger && !r.beneficiaire?.est_etranger) return false
      if (nq && !r._search.includes(nq)) return false
      return true
    })
    items.sort((a, b) => (b.montant || 0) - (a.montant || 0))
    return items
  }

  return {
    async getStats() {
      return stats
    },
    async getFilters() {
      const domaines = [...new Set(records.map((r) => r.domaine).filter(Boolean))].sort()
      const annees = [...new Set(records.map((r) => r.annee).filter(Boolean))].sort((a, b) => b - a)
      return { domaines, annees }
    },
    async search({ page = 1, pageSize = 20, ...filters } = {}) {
      const items = applyFilters(filters)
      const total = items.length
      const start = (page - 1) * pageSize
      return { items: items.slice(start, start + pageSize), total, totalCapped: false, page, pageSize }
    },
    async searchAll(filters = {}) {
      return applyFilters(filters)
    },
    async getBeneficiaire(id) {
      const subs = records.filter((r) => r.beneficiaire?.id === id)
      if (!subs.length) return null
      const b = subs[0].beneficiaire
      const total = subs.reduce((s, r) => s + (r.montant || 0), 0)
      const premiere = Math.min(...subs.map((r) => r.annee).filter(Boolean))
      subs.sort((a, b2) => (b2.annee || 0) - (a.annee || 0) || (b2.montant || 0) - (a.montant || 0))
      return { beneficiaire: b, subventions: subs, total, premiere_annee: premiere, n: subs.length }
    },
  }
}

/* ---------- Sélection de l'implémentation ---------- */

let _impl = null
let _loading = null

async function impl() {
  if (_impl) return _impl
  if (_loading) return _loading
  _loading = (async () => {
    const stats = await fetch(`${BASE}data/stats.json`).then((r) => r.json())
    const force = new URLSearchParams(window.location.search).get('data')
    const mode = force || stats?.meta?.detail || 'json'
    if (mode === 'sqlite') {
      const { createSqliteSource } = await import('./source.sqlite.js')
      _impl = await createSqliteSource(BASE, stats)
    } else {
      _impl = await createJsonSource(stats)
    }
    return _impl
  })()
  return _loading
}

export async function getStats() {
  return (await impl()).getStats()
}
export async function getFilters() {
  return (await impl()).getFilters()
}
export async function search(params) {
  return (await impl()).search(params)
}
export async function searchAll(filters) {
  return (await impl()).searchAll(filters)
}
export async function getBeneficiaire(id) {
  return (await impl()).getBeneficiaire(id)
}
