<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Chart from 'chart.js/auto'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
import { fmtDate } from '../format'

const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null
const rates = ref<{ month: string; rate: number | null }[]>([])

function monthsAgo(n: number): { y: number; m: number } {
  const d = new Date()
  d.setMonth(d.getMonth() - n)
  return { y: d.getFullYear(), m: d.getMonth() + 1 }
}

async function load() {
  const list: { month: string; rate: number | null }[] = []
  for (let n = 5; n >= 0; n--) {
    const { y, m } = monthsAgo(n)
    const r = await api.savingsRate(y, m)
    list.push({ month: `${y}-${String(m).padStart(2, '0')}-01`, rate: r.rate })
  }
  rates.value = list
  render()
}

function render() {
  if (!canvas.value || !rates.value.length) return
  const labels = rates.value.map((r) => fmtDate(r.month, { month: 'short', year: 'numeric' }))
  const data = rates.value.map((r) => (r.rate == null ? null : r.rate * 100))
  if (chart) {
    chart.data.labels = labels
    chart.data.datasets[0].data = data as any
    chart.update()
    return
  }
  chart = new Chart(canvas.value, {
    type: 'line',
    data: { labels, datasets: [{ data, borderColor: '#2d6a4f', backgroundColor: '#d8f3dc', fill: true, tension: 0.3, spanGaps: true }] },
    options: {
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${(c.parsed.y as number).toFixed(1)}%` } } },
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { ticks: { callback: (v) => `${v}%` } } },
    },
  })
}

onMounted(load)
watch(dataVersion, load)
</script>

<template>
  <div style="height: 200px"><canvas ref="canvas"></canvas></div>
</template>