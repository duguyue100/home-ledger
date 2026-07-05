<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
import { useSummary } from '../composables/useSummary'
import { i18n } from '../i18n'
import { money, percent } from '../format'
import CategoryBar from '../components/CategoryBar.vue'
import SavingsRateLine from '../components/SavingsRateLine.vue'
import BudgetVsActual from '../components/BudgetVsActual.vue'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))

function iso(d: Date): string { return d.toISOString().slice(0, 10) }
function todayIso(): string { return iso(new Date()) }
function monthStart(): string { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01` }
function yearStart(): string { return `${new Date().getFullYear()}-01-01` }
function curYM(): { y: number; m: number } { const d = new Date(); return { y: d.getFullYear(), m: d.getMonth() + 1 } }

const { data: daySum } = useSummary(() => 'day', todayIso)
const { data: monthSum } = useSummary(() => 'month', monthStart)
const { data: yearSum } = useSummary(() => 'year', yearStart)

const breakdown = ref<any[]>([])
async function loadBreakdown() {
  const { y, m } = curYM()
  breakdown.value = await api.breakdown(`${y}-${String(m).padStart(2, '0')}-01`, `${m === 12 ? y + 1 : y}-${String(m === 12 ? 1 : m + 1).padStart(2, '0')}-01`)
}
const budgetRows = ref<any[]>([])
async function loadBudget() {
  const { y, m } = curYM()
  budgetRows.value = await api.budgetVsActual(y, m)
}

const monthRate = ref<number | null>(null)
async function loadMonthRate() {
  const { y, m } = curYM()
  const r = await api.savingsRate(y, m)
  monthRate.value = r.rate
}

watch(dataVersion, () => { loadBreakdown(); loadBudget(); loadMonthRate() }, { immediate: true })

function netColor(n: number | undefined): string {
  if (n == null) return 'var(--ink)'
  return n >= 0 ? 'var(--accent)' : 'var(--red)'
}
</script>

<template>
  <h1 style="font-size:20px;margin-bottom:16px">{{ t('dash.title') }}</h1>

  <div class="tiles">
    <div class="tile">
      <div class="label">{{ t('dash.today') }}</div>
      <div class="value" :style="{ color: netColor(daySum?.net) }">{{ money(daySum?.net) }}</div>
      <div class="sub">−{{ money(daySum?.spending) }} +{{ money(daySum?.income) }}</div>
    </div>
    <div class="tile">
      <div class="label">{{ t('dash.thisMonth') }}</div>
      <div class="value" :style="{ color: netColor(monthSum?.net) }">{{ money(monthSum?.net) }}</div>
      <div class="sub">{{ t('dash.save') }} {{ percent(monthRate) }} · {{ t('dash.inv') }} {{ money(monthSum?.investment) }}</div>
    </div>
    <div class="tile">
      <div class="label">{{ t('dash.thisYear') }}</div>
      <div class="value" :style="{ color: netColor(yearSum?.net) }">{{ money(yearSum?.net) }}</div>
      <div class="sub">−{{ money(yearSum?.spending) }} +{{ money(yearSum?.income) }}</div>
    </div>
  </div>

  <div class="card" style="margin-top:16px">
    <div class="section-title">{{ t('dash.breakdown') }}</div>
    <CategoryBar :rows="breakdown" />
  </div>

  <div class="card" style="margin-top:16px">
    <div class="section-title">{{ t('dash.savings6') }}</div>
    <SavingsRateLine />
  </div>

  <div class="card" style="margin-top:16px">
    <div class="section-title">{{ t('dash.budgetVsActual') }}</div>
    <BudgetVsActual :rows="budgetRows" :locale="locale" />
  </div>
</template>