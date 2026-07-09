<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Chart from 'chart.js/auto'
import { api } from '../api'
import { i18n } from '../i18n'
import { dataVersion } from '../composables/useDataVersion'
import { fmtDate } from '../format'

const props = withDefaults(defineProps<{
  months?: number
  endYear?: number   // anchor end year (defaults to current)
  endMonth?: number   // anchor end month 1-12 (defaults to current)
}>(), {
  months: 12,
  endYear: () => new Date().getFullYear(),
  endMonth: () => new Date().getMonth() + 1,
})

const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null
const rates = ref<{ month: string; rate: number | null }[]>([])

function shiftBack(y: number, m: number, n: number): { y: number; m: number } {
  const d = new Date(y, m - 1, 1)
  d.setMonth(d.getMonth() - n)
  return { y: d.getFullYear(), m: d.getMonth() + 1 }
}

async function load() {
  const list: { month: string; rate: number | null }[] = []
  for (let n = props.months - 1; n >= 0; n--) {
    const { y, m } = shiftBack(props.endYear, props.endMonth, n)
    const r = await api.savingsRate(y, m)
    list.push({ month: `${y}-${String(m).padStart(2, '0')}-01`, rate: r.rate })
  }
  rates.value = list
  render()
}

function render() {
  if (!canvas.value || !rates.value.length) return
  const labels = rates.value.map((r) => fmtDate(r.month, { month: 'short', year: 'numeric' }))
  const data = rates.value.map((r) => (r.rate == null ? null : Math.round(r.rate * 1000) / 10))
  if (chart) {
    chart.data.labels = labels
    chart.data.datasets[0].data = data as any
    chart.update()
    return
  }
  chart = new Chart(canvas.value, {
    type: 'line',
    data: { labels, datasets: [{ data, borderColor: '#0f766e', backgroundColor: 'rgba(15,118,110,0.12)', fill: true, tension: 0.3, spanGaps: true }] },
    options: {
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${(c.parsed.y as number).toFixed(1)}%` } } },
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { ticks: { callback: (v) => `${Number(v).toFixed(1)}%` } } },
    },
  })
}

onMounted(load)
watch(() => [props.endYear, props.endMonth, props.months].join('|'), load)
watch(dataVersion, load)
watch(() => i18n.global.locale.value, render)
</script>

<template>
  <div style="height: 200px"><canvas ref="canvas"></canvas></div>
</template>