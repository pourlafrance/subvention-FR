<script setup>
import { computed } from 'vue'
import { formatEur } from '../lib/format.js'

// Mini-graphe en barres des montants reçus par année (SVG pur, sans dépendance).
const props = defineProps({ subventions: { type: Array, required: true } })

const serie = computed(() => {
  const par = new Map()
  for (const s of props.subventions) {
    if (!s.annee) continue
    par.set(s.annee, (par.get(s.annee) || 0) + (s.montant || 0))
  }
  const annees = [...par.keys()].sort()
  if (annees.length < 2) return []
  // Années creuses incluses (barre à zéro) pour ne pas masquer une interruption.
  const out = []
  for (let a = annees[0]; a <= annees[annees.length - 1]; a++) {
    out.push({ annee: a, montant: par.get(a) || 0 })
  }
  return out
})

const W = 320
const H = 64
const bars = computed(() => {
  const max = Math.max(...serie.value.map((d) => d.montant), 1)
  const n = serie.value.length
  const bw = Math.min(28, (W - (n - 1) * 4) / n)
  return serie.value.map((d, i) => ({
    ...d,
    x: i * (bw + 4),
    w: bw,
    h: Math.max(d.montant > 0 ? 2 : 0, (d.montant / max) * (H - 16)),
  }))
})
</script>

<template>
  <div v-if="serie.length" class="sparkline">
    <svg :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H" role="img"
         :aria-label="`Montants reçus par année, de ${serie[0].annee} à ${serie[serie.length - 1].annee}`">
      <g v-for="b in bars" :key="b.annee">
        <rect :x="b.x" :y="H - 14 - b.h" :width="b.w" :height="b.h" fill="#000091" rx="1.5">
          <title>{{ b.annee }} : {{ formatEur(b.montant) }}</title>
        </rect>
        <text :x="b.x + b.w / 2" :y="H - 3" text-anchor="middle"
              font-size="8.5" fill="#666" class="num">{{ String(b.annee).slice(2) }}</text>
      </g>
    </svg>
  </div>
</template>
