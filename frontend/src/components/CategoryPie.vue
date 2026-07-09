<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Chart from 'chart.js/auto'
import { i18n } from '../i18n'
import { money, percent } from '../format'

const props = defineProps<{ rows: any[] }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

const PALETTE = [
  '#0f766e', '#1e3a8a', '#b45309', '#7c2d12', '#4a044e',
  '#1f2937', '#0e7490', '#9f1239', '#365314', '#5b21b6',
]

function labelOf(r: any): string {
  return i18n.global.locale.value === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en
}

function render() {
  if (!canvas.value || !props.rows.length) return
  const labels = props.rows.map(labelOf)
  const data = props.rows.map((r) => r.total / 100)
  const total = data.reduce((s, v) => s + v, 0)
  if (chart) {
    chart.data.labels = labels
    chart.data.datasets[0].data = data
    chart.update()
    return
  }
  chart = new Chart(canvas.value, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: props.rows.map((_, i) => PALETTE[i % PALETTE.length]),
        borderColor: '#fff',
        borderWidth: 2,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => {
              const v = c.parsed as number
              const share = total ? v / total : 0
              return `${c.label}: ${money(Math.round(v * 100))} · ${percent(share)}`
            },
          },
        },
      },
      responsive: true,
      maintainAspectRatio: false,
      cutout: '58%',
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
  <div style="height: 280px; position: relative">
    <canvas ref="canvas"></canvas>
    <div v-if="rows.length" class="center-total" aria-hidden="true">
      <div class="ct-label">Total</div>
      <div class="ct-value">{{ money(rows.reduce((s, r) => s + r.total, 0)) }}</div>
    </div>
  </div>
</template>

<style scoped>
.center-total {
  position: absolute;
  top: 50%; left: 50%; transform: translate(-50%, -50%);
  text-align: center; pointer-events: none; line-height: 1.2;
}
.ct-label { font-size: 11px; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.04em; }
.ct-value { font-size: 18px; font-weight: 600; font-variant-numeric: tabular-nums; margin-top: 2px; }
</style>