<script setup>
import { computed } from 'vue'
import { formatEur, formatInt } from '../lib/format.js'
import geo from '../assets/departements-svg.json'

// data : { liste: [{ code, volume_eur, count }], part_geolocalisee }
// Carte choroplèthe SVG pure (géométrie committée, aucune dépendance).
// Les départements d'outre-mer (97x/98x), absents du fond métropolitain,
// sont listés sous la carte — jamais omis en silence.
const props = defineProps({ data: { type: Object, required: true } })

const parCode = computed(() => new Map((props.data.liste || []).map((d) => [d.code, d])))
const maxVol = computed(() => Math.max(...(props.data.liste || []).map((d) => d.volume_eur), 1))

function opacite(code) {
  const d = parCode.value.get(code)
  if (!d || !d.volume_eur) return 0.04
  // Échelle racine : lisible malgré les ordres de grandeur d'écart.
  return 0.08 + 0.92 * Math.sqrt(d.volume_eur / maxVol.value)
}
function libelle(dep) {
  const d = parCode.value.get(dep.code)
  return d
    ? `${dep.nom} (${dep.code}) : ${formatEur(d.volume_eur)} — ${formatInt(d.count)} subventions`
    : `${dep.nom} (${dep.code}) : aucune subvention géolocalisée`
}

const NOMS_OUTREMER = {
  '971': 'Guadeloupe', '972': 'Martinique', '973': 'Guyane', '974': 'La Réunion',
  '975': 'Saint-Pierre-et-Miquelon', '976': 'Mayotte', '977': 'Saint-Barthélemy',
  '978': 'Saint-Martin', '986': 'Wallis-et-Futuna', '987': 'Polynésie française',
  '988': 'Nouvelle-Calédonie',
}
const outremer = computed(() =>
  (props.data.liste || [])
    .filter((d) => d.code.length === 3)
    .map((d) => ({ ...d, nom: NOMS_OUTREMER[d.code] || `Territoire ${d.code}` })),
)
</script>

<template>
  <div class="chart-wrap">
    <svg :viewBox="geo.viewBox" role="img" style="width:100%;max-width:640px;display:block;margin:0 auto"
         aria-label="Carte de France des subventions par département">
      <path v-for="dep in geo.departements" :key="dep.code" :d="dep.d"
            fill="#000091" :fill-opacity="opacite(dep.code)"
            stroke="#fff" stroke-width="0.6">
        <title>{{ libelle(dep) }}</title>
      </path>
    </svg>
    <div v-if="outremer.length" class="muted" style="font-size:.85rem;margin-top:10px">
      Outre-mer&nbsp;:
      <template v-for="(d, i) in outremer" :key="d.code">
        <template v-if="i">&nbsp;· </template>{{ d.nom }} <span class="num">{{ formatEur(d.volume_eur) }}</span>
      </template>
    </div>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">
      Département du siège du bénéficiaire (survolez pour le détail).
      {{ (data.part_geolocalisee * 100).toLocaleString('fr-FR', { maximumFractionDigits: 0 }) }}&nbsp;% du volume
      documenté est géolocalisable&nbsp;; le reste n'est pas masqué, il n'est pas localisé par les sources.
    </p>
  </div>
</template>
