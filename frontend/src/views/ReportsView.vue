<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
import { i18n } from '../i18n'
import { useCategories, categoryName, findCategory } from '../composables/useCategories'
import { money, percent, fmtDate } from '../format'
import CategoryBar from '../components/CategoryBar.vue'
import SavingsRateLine from '../components/SavingsRateLine.vue'
import BudgetVsActual from '../components/BudgetVsActual.vue'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))
const { categories } = useCategories()

type Period = 'month' | 'year'
const period = ref<Period>('month')

function curMonth(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
function curYear(): number { return new Date().getFullYear() }

const monthStr = ref(curMonth())
const yearNum = ref(curYear())

const refIso = computed(() =>
  period.value === 'month' ? `${monthStr.value}-01` : `${yearNum.value}-01-01`
)
const anchorYear = computed(() =>
  period.value === 'month'
    ? Number(monthStr.value.split('-')[0])
    : yearNum.value
)
const anchorMonth = computed(() =>
  period.value === 'month'
    ? Number(monthStr.value.split('-')[1])
    : 12
)

const report = ref<any>(null)
const top5 = ref<any[]>([])
const loading = ref(false)
const err = ref<string | null>(null)

async function load() {
  loading.value = true
  err.value = null
  try {
    report.value = await api.report(refIso.value, period.value)
    const from = period.value === 'month'
      ? `${monthStr.value}-01`
      : `${yearNum.value}-01-01`
    const to = period.value === 'month'
      ? nextMonth(monthStr.value)
      : `${yearNum.value + 1}-01-01`
    const r = await api.transactions({ from, to, limit: 1000 })
    top5.value = [...r].sort((a, b) => b.amount - a.amount).slice(0, 5)
  } catch (e: any) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}

function nextMonth(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  const ny = m === 12 ? y + 1 : y
  const nm = m === 12 ? 1 : m + 1
  return `${ny}-${String(nm).padStart(2, '0')}-01`
}

watch([period, monthStr, yearNum], load, { immediate: true })
watch(dataVersion, load)

const totalSpending = computed(() =>
  report.value?.breakdown.reduce((s: number, r: any) => s + r.total, 0) || 0
)

function printPage() { window.print() }
function fmtMonthLabel(m: number): string {
  return fmtDate(`${anchorYear.value}-${String(m).padStart(2, '0')}-01`, { month: 'short' })
}
</script>

<template>
  <div class="row" style="margin-bottom: 16px; gap: 12px; flex-wrap: wrap">
    <h1 style="font-size: 20px; margin: 0">{{ t('report.title') }}</h1>
    <div class="seg no-print" role="tablist">
      <button :class="{ active: period === 'month' }" @click="period = 'month'">{{ t('report.month') }}</button>
      <button :class="{ active: period === 'year' }" @click="period = 'year'">{{ t('report.year') }}</button>
    </div>
    <input v-if="period === 'month'" type="month" v-model="monthStr" />
    <input v-else type="number" min="2000" max="2100" v-model.number="yearNum"
           style="width: 100px; font-variant-numeric: tabular-nums" />
    <button class="btn no-print" style="margin-left: auto" @click="printPage">{{ t('report.print') }}</button>
  </div>

  <div v-if="loading" class="empty">{{ t('common.loading') }}</div>
  <div v-else-if="err" class="err">{{ err }}</div>
  <div v-else-if="report">
    <!-- savings rate trend line, always 12 months ending at the anchor -->
    <div class="card">
      <div class="section-title">{{ t('report.savingsRateRolling') }}</div>
      <SavingsRateLine :months="12" :end-year="anchorYear" :end-month="anchorMonth" />
    </div>

    <!-- summary tiles -->
    <div class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.summary') }}</div>
      <div class="tiles" style="margin-top: 8px">
        <div class="tile">
          <div class="label">{{ t('kind.income') }}</div>
          <div class="value" style="color: var(--accent)">{{ money(report.summary.income) }}</div>
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
          <div class="value" :style="{ color: report.summary.net >= 0 ? 'var(--accent)' : 'var(--red)' }">
            {{ money(report.summary.net) }}
          </div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsRate') }}</div>
          <div class="value">{{ percent(report.savings_rate) }}</div>
        </div>
      </div>
    </div>

    <!-- breakdown -->
    <div class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.byCategory') }}</div>
      <CategoryBar v-if="report.breakdown.length" :rows="report.breakdown" />
      <table v-if="report.breakdown.length" class="data-table" style="margin-top: 12px">
        <thead>
          <tr>
            <th>{{ t('report.category') }}</th>
            <th class="num">{{ t('report.total') }}</th>
            <th class="num">{{ t('report.share') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in report.breakdown" :key="r.category_id">
            <td>{{ locale === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en }}</td>
            <td class="num">{{ money(r.total) }}</td>
            <td class="num" style="color: var(--ink-soft)">
              {{ totalSpending ? percent(r.total / totalSpending) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">—</div>
    </div>

    <!-- budget vs actual -->
    <div class="card" style="margin-top: 16px">
      <div class="section-title">
        {{ period === 'year' ? t('report.budgetVsActualYear') : t('report.budgetVsActual') }}
      </div>
      <BudgetVsActual :rows="report.budget_vs_actual" :locale="locale as string" />
    </div>

    <!-- monthly breakdown (yearly mode only) -->
    <div v-if="period === 'year' && report.monthly" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.monthlyBreakdown') }}</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('report.month') }}</th>
            <th class="num">{{ t('kind.income') }}</th>
            <th class="num">{{ t('kind.spending') }}</th>
            <th class="num">{{ t('kind.investment') }}</th>
            <th class="num">{{ t('report.net') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in report.monthly" :key="m.m">
            <td>{{ fmtMonthLabel(m.m) }}</td>
            <td class="num" style="color: var(--accent)">{{ money(m.income) }}</td>
            <td class="num">{{ money(m.spending) }}</td>
            <td class="num">{{ money(m.investment) }}</td>
            <td class="num" :style="{ color: m.net >= 0 ? 'var(--accent)' : 'var(--red)' }">
              {{ money(m.net) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- top 5 -->
    <div class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.top5') }}</div>
      <div v-if="!top5.length" class="empty">—</div>
      <div v-for="txn in top5" :key="txn.id" class="txn-card" style="margin-top: 0">
        <span class="kind-dot" :class="txn.kind"></span>
        <div>
          <div class="note">{{ txn.note || t(`kind.${txn.kind}`) }}</div>
          <div class="cat">
            {{ categoryName(findCategory(txn.category_id), locale as string) }}
            <span class="muted">· {{ fmtDate(txn.occurred_on, { day: 'numeric', month: 'short', year: 'numeric' }) }}</span>
          </div>
        </div>
        <div class="amount" :class="txn.kind" style="margin-left: auto">{{ money(txn.amount) }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}
.seg button {
  padding: 6px 14px;
  font-size: 13px;
  color: var(--ink-soft);
  background: transparent;
}
.seg button.active {
  background: var(--accent);
  color: #fff;
}
</style>