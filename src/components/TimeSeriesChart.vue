<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Chart, LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js'
import { formatEur } from '../lib/format.js'

Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend)

// serie : [{ annee, montant, montant_constant? }] — la série en euros constants
// n'est tracée que si le pipeline l'a produite (table IPC présente).
const props = defineProps({ serie: { type: Array, default: () => [] } })
const emit = defineEmits(['select'])
const canvas = ref(null)
let chart = null

function render() {
  if (!canvas.value) return
  const data = [...props.serie].sort((a, b) => a.annee - b.annee)
  const hasConstant = data.some((d) => d.montant_constant != null)
  if (chart) chart.destroy()
  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: data.map((d) => d.annee),
      datasets: [
        {
          label: 'Euros courants',
          data: data.map((d) => d.montant),
          borderColor: '#000091',
          backgroundColor: '#000091',
          pointRadius: 3,
          tension: 0.15,
        },
        ...(hasConstant ? [{
          label: 'Euros constants',
          data: data.map((d) => d.montant_constant),
          borderColor: '#6a6af4',
          backgroundColor: '#6a6af4',
          borderDash: [5, 4],
          pointRadius: 3,
          tension: 0.15,
        }] : []),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (_e, els) => { if (els.length) emit('select', data[els[0].index].annee) },
      plugins: {
        legend: { display: hasConstant, labels: { boxWidth: 18, font: { size: 12 } } },
        tooltip: { callbacks: { label: (c) => `${c.dataset.label} : ${formatEur(c.raw)}` } },
      },
      scales: {
        y: { ticks: { callback: (v) => formatEur(v) }, grid: { color: '#eee' }, beginAtZero: true },
        x: { grid: { display: false }, ticks: { font: { size: 12 } } },
      },
    },
  })
}

onMounted(render)
watch(() => props.serie, render, { deep: true })
onBeforeUnmount(() => chart && chart.destroy())
</script>

<template>
  <div class="chart-wrap">
    <div style="height:260px">
      <canvas ref="canvas"></canvas>
    </div>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">
      Cliquez un point pour voir les subventions de l'année. Volume total documenté, toutes sources confondues.
    </p>
  </div>
</template>
