<script setup>
import { computed } from 'vue'
import { formatEur, formatInt } from '../lib/format.js'
import geo from '../assets/departements-svg.json'

// data : { liste: [{ code, volume_eur, count }], part_geolocalisee }
// Carte choroplèthe SVG pure (géométrie committée, aucune dépendance) :
//  - rampe séquentielle clair -> rouge foncé (plus le volume est élevé, plus
//    c'est rouge), échelle racine pour absorber les ordres de grandeur ;
//  - médaillon Île-de-France (la petite couronne est illisible sinon) ;
//  - légende avec bornes réelles ; outre-mer listé, jamais omis en silence.
const props = defineProps({ data: { type: Object, required: true } })

const parCode = computed(() => new Map((props.data.liste || []).map((d) => [d.code, d])))
const maxVol = computed(() => Math.max(...(props.data.liste || []).map((d) => d.volume_eur), 1))

// Rampe OrRd (ColorBrewer), interpolation linéaire entre paliers.
const STOPS = [
  [255, 247, 236], [253, 212, 158], [252, 141, 89], [215, 48, 31], [127, 0, 0],
]
function rampe(t) {
  const pos = Math.min(Math.max(t, 0), 1) * (STOPS.length - 1)
  const i = Math.min(Math.floor(pos), STOPS.length - 2)
  const f = pos - i
  const c = STOPS[i].map((v, k) => Math.round(v + f * (STOPS[i + 1][k] - v)))
  return `rgb(${c[0]},${c[1]},${c[2]})`
}
const degrade = `linear-gradient(to right, ${[0, 0.25, 0.5, 0.75, 1].map((t) => rampe(t)).join(', ')})`

function couleur(code) {
  const d = parCode.value.get(code)
  if (!d || !d.volume_eur) return '#ececec'
  return rampe(Math.sqrt(d.volume_eur / maxVol.value))
}
function libelle(dep) {
  const d = parCode.value.get(dep.code)
  return d
    ? `${dep.nom} (${dep.code}) : ${formatEur(d.volume_eur)} — ${formatInt(d.count)} subventions`
    : `${dep.nom} (${dep.code}) : aucune subvention géolocalisée`
}

const IDF = new Set(['75', '77', '78', '91', '92', '93', '94', '95'])
const idf = computed(() => geo.departements.filter((d) => IDF.has(d.code)))

const NOMS_OUTREMER = {
  '971': 'Guadeloupe', '972': 'Martinique', '973': 'Guyane', '974': 'La Réunion',
  '975': 'Saint-Pierre-et-Miquelon', '976': 'Mayotte', '977': 'Saint-Barthélemy',
  '978': 'Saint-Martin', '986': 'Wallis-et-Futuna', '987': 'Polynésie française',
  '988': 'Nouvelle-Calédonie',
}
const outremer = computed(() =>
  (props.data.liste || [])
    .filter((d) => d.code in NOMS_OUTREMER)
    .map((d) => ({ ...d, nom: NOMS_OUTREMER[d.code] })),
)
</script>

<template>
  <div class="chart-wrap">
    <div style="position:relative">
      <svg :viewBox="geo.viewBox" role="img" style="width:100%;max-width:640px;display:block;margin:0 auto"
           aria-label="Carte de France des subventions par département">
        <path v-for="dep in geo.departements" :key="dep.code" :d="dep.d"
              :fill="couleur(dep.code)" stroke="#fff" stroke-width="0.6">
          <title>{{ libelle(dep) }}</title>
        </path>
      </svg>
      <!-- Médaillon Île-de-France -->
      <div style="position:absolute;top:0;right:0;width:27%;max-width:170px;background:var(--surface);border:1px solid var(--line-strong);border-radius:6px;padding:6px 6px 2px">
        <svg :viewBox="geo.idfViewBox" role="img" style="width:100%;display:block"
             aria-label="Zoom sur l'Île-de-France">
          <path v-for="dep in idf" :key="dep.code" :d="dep.d"
                :fill="couleur(dep.code)" stroke="#fff" stroke-width="0.5">
            <title>{{ libelle(dep) }}</title>
          </path>
        </svg>
        <div class="muted" style="font-size:.7rem;text-align:center;padding:3px 0 2px">Île-de-France</div>
      </div>
    </div>

    <!-- Échelle -->
    <div style="display:flex;align-items:center;gap:10px;margin-top:14px;flex-wrap:wrap">
      <span class="muted num" style="font-size:.8rem">0&nbsp;€</span>
      <div :style="{ background: degrade, height: '10px', flex: '1', minWidth: '140px', maxWidth: '320px', borderRadius: '5px', border: '1px solid var(--line)' }"
           role="img" aria-label="Échelle des couleurs, du plus clair (faible volume) au rouge foncé (volume le plus élevé)"></div>
      <span class="muted num" style="font-size:.8rem">{{ formatEur(maxVol) }}</span>
      <span style="display:inline-flex;align-items:center;gap:5px;font-size:.8rem" class="muted">
        <span style="width:14px;height:10px;background:#ececec;border:1px solid var(--line);border-radius:3px"></span>
        aucune donnée
      </span>
    </div>

    <div v-if="outremer.length" class="muted" style="font-size:.85rem;margin-top:10px">
      Outre-mer&nbsp;:
      <template v-for="(d, i) in outremer" :key="d.code">
        <template v-if="i">&nbsp;· </template>{{ d.nom }} <span class="num">{{ formatEur(d.volume_eur) }}</span>
      </template>
    </div>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">
      Département du siège du bénéficiaire (survolez pour le détail), échelle racine (√), toute période confondue.
      {{ (data.part_geolocalisee * 100).toLocaleString('fr-FR', { maximumFractionDigits: 0 }) }}&nbsp;% du volume
      documenté est géolocalisable&nbsp;; le reste n'est pas masqué, il n'est pas localisé par les sources.
    </p>
  </div>
</template>
