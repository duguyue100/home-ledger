<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
import { i18n } from '../i18n'
import { findCategory, categoryName } from '../composables/useCategories'
import { money, percent, fmtDate } from '../format'
import BudgetVsActual from '../components/BudgetVsActual.vue'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))

function curMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
const month = ref(curMonth())
const report = ref<any>(null)
const top5 = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    report.value = await api.report(month.value + '-01')
    // top 5 by amount (any kind)
    const r = await api.transactions({ from: month.value + '-01', to: nextMonth(), limit: 1000 })
    top5.value = [...r].sort((a, b) => b.amount - a.amount).slice(0, 5)
  } finally {
    loading.value = false
  }
}
function nextMonth(): string {
  const [y, m] = month.value.split('-').map(Number)
  const ny = m === 12 ? y + 1 : y
  const nm = m === 12 ? 1 : m + 1
  return `${ny}-${String(nm).padStart(2, '0')}-01`
}
watch(month, load, { immediate: true })
watch(dataVersion, load)

const totalSpending = computed(() =>
  report.value?.breakdown.reduce((s: number, r: any) => s + r.total, 0) || 0
)
function printPage() { window.print() }
</script>

<template>
  <div class="row" style="margin-bottom:16px">
    <h1 style="font-size:20px;margin:0">{{ t('report.title') }}</h1>
    <input type="month" v-model="month" style="width:160px" />
    <button class="btn no-print" style="margin-left:auto" @click="printPage">{{ t('report.print') }}</button>
  </div>

  <div v-if="loading" class="empty">{{ t('common.loading') }}</div>
  <div v-else-if="report">
    <div class="card">
      <div class="section-title">{{ t('report.summary') }}</div>
      <div class="tiles" style="margin-top:8px">
        <div class="tile">
          <div class="label">{{ t('kind.income') }}</div>
          <div class="value" style="color:var(--accent)">{{ money(report.summary.income) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('kind.spending') }}</div>
          <div class="value">{{ money(report.summary.spending) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('kind.investment') }}</div>
          <div class="value">{{ money(report.summary.investment) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.net') }}</div>
          <div class="value" :style="{ color: report.summary.net >= 0 ? 'var(--accent)' : 'var(--red)' }">{{ money(report.summary.net) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsRate') }}</div>
          <div class="value">{{ percent(report.savings_rate) }}</div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <div class="section-title">{{ t('report.byCategory') }}</div>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="text-align:left;color:var(--ink-soft);font-size:12px">
            <th style="padding:6px 0;border-bottom:1px solid var(--line)">{{ t('report.category') }}</th>
            <th style="text-align:right;padding:6px 0;border-bottom:1px solid var(--line)">{{ t('report.total') }}</th>
            <th style="text-align:right;padding:6px 0;border-bottom:1px solid var(--line)">{{ t('report.share') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in report.breakdown" :key="r.category_id">
            <td style="padding:8px 0;border-bottom:1px solid var(--line)">
              {{ locale === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en }}
            </td>
            <td style="text-align:right;padding:8px 0;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums">{{ money(r.total) }}</td>
            <td style="text-align:right;padding:8px 0;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;color:var(--ink-soft)">
              {{ totalSpending ? percent(r.total / totalSpending) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top:16px">
      <div class="section-title">{{ t('report.budgetVsActual') }}</div>
      <BudgetVsActual :rows="report.budget_vs_actual" :locale="locale as string" />
    </div>

    <div class="card" style="margin-top:16px">
      <div class="section-title">{{ t('report.top5') }}</div>
      <div v-for="t in top5" :key="t.id" class="txn-card" style="margin-top:0">
        <span class="kind-dot" :class="t.kind"></span>
        <div>
          <div class="note">{{ t.note || t(`kind.${t.kind}`) }}</div>
          <div class="cat">
            {{ categoryName(findCategory(t.category_id), locale as string) }}
            <span class="muted">· {{ fmtDate(t.occurred_on, { day: 'numeric', month: 'short', year: 'numeric' }) }}</span>
          </div>
        </div>
        <div class="amount" :class="t.kind" style="margin-left:auto">{{ money(t.amount) }}</div>
      </div>
    </div>
  </div>
</template>