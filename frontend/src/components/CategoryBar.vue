<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Chart from 'chart.js/auto'
import { i18n } from '../i18n'

const props = defineProps<{ rows: any[] }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

function loc(): string {
  return i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'
}
function labelOf(r: any): string {
  return loc() === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en
}

function render() {
  if (!canvas.value) return
  const labels = props.rows.map(labelOf)
  const data = props.rows.map((r) => r.total / 100)
  if (chart) {
    chart.data.labels = labels
    chart.data.datasets[0].data = data
    chart.update()
    return
  }
  chart = new Chart(canvas.value, {
    type: 'bar',
    data: { labels, datasets: [{ data, backgroundColor: '#2d6a4f', borderRadius: 4 }] },
    options: {
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `CHF ${c.parsed.y}` } } },
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { grid: { display: false } }, y: { ticks: { callback: (v) => `CHF ${v}` } } },
    },
  })
}

onMounted(() => {
  Chart.defaults.font.family = '-apple-system, "PingFang SC", sans-serif'
  render()
})
watch(() => props.rows, render, { deep: true })
watch(() => i18n.global.locale.value, render)
</script>

<template>
  <div style="height: 240px"><canvas ref="canvas"></canvas></div>
</template>