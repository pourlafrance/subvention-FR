<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Chart, BarController, BarElement, CategoryScale, LinearScale, Tooltip } from 'chart.js'
import { formatEur } from '../lib/format.js'

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip)

const props = defineProps({ domaines: { type: Array, default: () => [] } })
const emit = defineEmits(['select'])
const canvas = ref(null)
let chart = null

function render() {
  if (!canvas.value) return
  const data = [...props.domaines].sort((a, b) => b.volume_eur - a.volume_eur).slice(0, 12)
  if (chart) chart.destroy()
  chart = new Chart(canvas.value, {
    type: 'bar',
    data: {
      labels: data.map((d) => d.domaine),
      datasets: [{ data: data.map((d) => d.volume_eur), backgroundColor: '#000091', borderRadius: 3, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      onClick: (_e, els) => { if (els.length) emit('select', data[els[0].index].domaine) },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => formatEur(c.raw) } },
      },
      scales: {
        x: { ticks: { callback: (v) => formatEur(v) }, grid: { color: '#eee' } },
        y: { grid: { display: false }, ticks: { font: { size: 12 } } },
      },
    },
  })
}

onMounted(render)
watch(() => props.domaines, render, { deep: true })
onBeforeUnmount(() => chart && chart.destroy())
</script>

<template>
  <div class="chart-wrap">
    <div :style="{ height: Math.max(220, domaines.length * 26) + 'px' }">
      <canvas ref="canvas"></canvas>
    </div>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">
      Cliquez une barre pour voir les subventions du domaine. Classement par fonction COFOG (INSEE).
    </p>
  </div>
</template>
