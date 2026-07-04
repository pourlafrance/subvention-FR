<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { search, searchAll, getFilters } from '../data/source.js'
import { formatEur, TYPE_LABELS } from '../lib/format.js'
import SubventionRow from '../components/SubventionRow.vue'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const router = useRouter()

const q = ref('')
const type = ref('')
const domaine = ref('')
const annee = ref('')
const etranger = ref(false)
const page = ref(1)

const result = ref({ items: [], total: 0 })
const filters = ref({ domaines: [], annees: [] })
const loading = ref(true)
const pageSize = 20

function fromRoute() {
  q.value = route.query.q || ''
  type.value = route.query.type || ''
  domaine.value = route.query.domaine || ''
  annee.value = route.query.annee || ''
  etranger.value = route.query.etranger === '1'
  page.value = Number(route.query.page) || 1
}

async function run() {
  loading.value = true
  result.value = await search({
    q: q.value, type: type.value, domaine: domaine.value,
    annee: annee.value, etranger: etranger.value, page: page.value, pageSize,
  })
  loading.value = false
}

function pushQuery(extra = {}) {
  const query = {}
  if (q.value) query.q = q.value
  if (type.value) query.type = type.value
  if (domaine.value) query.domaine = domaine.value
  if (annee.value) query.annee = annee.value
  if (etranger.value) query.etranger = '1'
  Object.assign(query, extra)
  router.push({ name: 'liste', query })
}

function applyFilters() { page.value = 1; pushQuery({ page: undefined }) }
function setPage(p) { pushQuery({ page: p }) }
function reset() { router.push({ name: 'liste', query: {} }) }

const volumePage = computed(() => result.value.items.reduce((s, r) => s + (r.montant || 0), 0))

// Export CSV des résultats filtrés (F5). Point-virgule + BOM : ouvre proprement
// dans les tableurs configurés en français.
function csvCell(v) {
  const s = v == null ? '' : String(v)
  return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
}
async function exportCsv() {
  let items = await searchAll({
    q: q.value, type: type.value, domaine: domaine.value,
    annee: annee.value, etranger: etranger.value,
  })
  // En mode SQLite, searchAll est plafonné (EXPORT_MAX = 5000) : on prévient
  // plutôt que d'exporter silencieusement un fichier incomplet.
  if (items.length > 5000) {
    items = items.slice(0, 5000)
    window.alert('Export limité aux 5 000 premières lignes (par montant décroissant). Affinez les filtres pour un export complet.')
  }
  const header = ['beneficiaire', 'type', 'siren', 'annee', 'montant_eur', 'domaine', 'objet', 'financeur', 'source', 'source_url']
  const lines = items.map((r) => [
    r.beneficiaire?.nom, r.beneficiaire?.type, r.beneficiaire?.siren, r.annee, r.montant,
    r.domaine, r.objet, r.financeur_nom, r.source, r.source_url,
  ].map(csvCell).join(';'))
  const blob = new Blob(['\uFEFF' + [header.join(';'), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'subventions-fr-export.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

onMounted(async () => {
  filters.value = await getFilters()
  fromRoute()
  await run()
})
watch(() => route.query, async () => { fromRoute(); await run() })
</script>

<template>
  <h1>Rechercher une subvention</h1>

  <div class="card">
    <div class="search">
      <input type="text" v-model="q" placeholder="Nom de bénéficiaire ou objet…"
             @keyup.enter="applyFilters" aria-label="Recherche texte" />
      <select v-model="type" @change="applyFilters" aria-label="Type de bénéficiaire">
        <option value="">Tous les types</option>
        <option v-for="(lab, val) in TYPE_LABELS" :key="val" :value="val">{{ lab }}</option>
      </select>
      <select v-model="domaine" @change="applyFilters" aria-label="Domaine">
        <option value="">Tous les domaines</option>
        <option v-for="d in filters.domaines" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="annee" @change="applyFilters" aria-label="Année">
        <option value="">Toutes les années</option>
        <option v-for="a in filters.annees" :key="a" :value="a">{{ a }}</option>
      </select>
    </div>
    <label style="display:inline-flex;align-items:center;gap:8px;margin-top:12px;font-size:.9rem;cursor:pointer">
      <input type="checkbox" v-model="etranger" @change="applyFilters" />
      Bénéficiaires hors France uniquement
    </label>
  </div>

  <div style="display:flex;align-items:baseline;justify-content:space-between;margin-top:18px;gap:12px;flex-wrap:wrap">
    <p class="muted" style="margin:0">
      <span class="num">{{ result.total }}<template v-if="result.totalCapped">+</template></span> résultat<span v-if="result.total > 1">s</span>
      <template v-if="result.total"> · <span class="num">{{ formatEur(volumePage) }}</span> sur cette page</template>
    </p>
    <div style="display:flex;gap:8px">
      <button v-if="result.total" class="btn ghost" @click="exportCsv">Exporter CSV</button>
      <button class="btn ghost" @click="reset">Réinitialiser</button>
    </div>
  </div>

  <div v-if="loading" class="empty">Chargement…</div>
  <div v-else-if="!result.items.length" class="empty">
    Aucune subvention ne correspond à ces critères.
  </div>
  <div v-else class="rows">
    <SubventionRow v-for="r in result.items" :key="r.id" :record="r" />
  </div>

  <Pagination :page="page" :page-size="pageSize" :total="result.total" @update:page="setPage" />
</template>
