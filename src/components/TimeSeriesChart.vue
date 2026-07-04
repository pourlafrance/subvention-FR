<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import {
  Chart, BarController, BarElement, LineController, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend,
} from 'chart.js'
import { formatEur } from '../lib/format.js'

Chart.register(BarController, BarElement, LineController, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend)

// serie      : [{ annee, montant, montant_constant? }] — totaux annuels
// parSource  : [{ source, serie: [{ annee, montant }] }] — ventilation, empilée
// La couverture des sources varie selon les années : les barres empilées
// montrent QUI documente quoi, au lieu de faire passer un élargissement de
// données pour une évolution de l'effort public.
const props = defineProps({
  serie: { type: Array, default: () => [] },
  parSource: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])
const canvas = ref(null)
let chart = null

const PALETTE = ['#000091', '#6a6af4', '#e4794a', '#009081', '#9898f8', '#666666']

// Fenêtre d'affichage : on masque la traîne d'années anciennes quasi vides
// (< 0,5 % du maximum annuel), en le disant (masquees exposé à la vue).
const fenetre = computed(() => {
  const data = [...props.serie].sort((a, b) => a.annee - b.annee)
  if (!data.length) return { annees: [], masquees: null }
  const max = Math.max(...data.map((d) => d.montant || 0))
  const seuil = max * 0.005
  const debut = data.find((d) => (d.montant || 0) >= seuil)?.annee ?? data[0].annee
  const annees = []
  for (let a = debut; a <= data[data.length - 1].annee; a++) annees.push(a)
  const avant = data.filter((d) => d.annee < debut)
  return {
    annees,
    masquees: avant.length
      ? { jusqu: debut - 1, total: avant.reduce((s, d) => s + (d.montant || 0), 0) }
      : null,
  }
})

function render() {
  if (!canvas.value) return
  const { annees } = fenetre.value
  if (!annees.length) return
  const idx = new Map(annees.map((a, i) => [a, i]))
  const barres = props.parSource.map((s, i) => {
    const data = new Array(annees.length).fill(0)
    for (const e of s.serie) if (idx.has(e.annee)) data[idx.get(e.annee)] = e.montant
    return {
      type: 'bar', label: s.source, data, stack: 'total',
      backgroundColor: PALETTE[i % PALETTE.length], maxBarThickness: 34,
    }
  })
  const constants = props.serie.some((d) => d.montant_constant != null)
    ? [{
        type: 'line', label: 'Total en euros constants',
        data: annees.map((a) => props.serie.find((d) => d.annee === a)?.montant_constant ?? null),
        borderColor: '#161616', backgroundColor: '#161616',
        borderDash: [5, 4], pointRadius: 2, tension: 0.15,
      }]
    : []
  if (chart) chart.destroy()
  chart = new Chart(canvas.value, {
    data: { labels: annees, datasets: [...constants, ...barres] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (_e, els) => { if (els.length) emit('select', annees[els[0].index]) },
      plugins: {
        legend: { labels: { boxWidth: 14, font: { size: 11 } } },
        tooltip: {
          callbacks: { label: (c) => `${c.dataset.label} : ${formatEur(c.raw)}` },
        },
      },
      scales: {
        y: { stacked: true, ticks: { callback: (v) => formatEur(v) }, grid: { color: '#eee' }, beginAtZero: true },
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 12 } } },
      },
    },
  })
}

onMounted(render)
watch(() => [props.serie, props.parSource], render, { deep: true })
onBeforeUnmount(() => chart && chart.destroy())
</script>

<template>
  <div class="chart-wrap">
    <div style="height:300px">
      <canvas ref="canvas"></canvas>
    </div>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">
      Cliquez une année pour voir ses subventions. Chaque source ne couvre que certains exercices&nbsp;:
      les creux traduisent d'abord des trous de publication.
      <template v-if="fenetre.masquees">
        Années antérieures à {{ fenetre.masquees.jusqu + 1 }} non affichées
        ({{ formatEur(fenetre.masquees.total) }} cumulés, volumes marginaux).
      </template>
    </p>
  </div>
</template>
