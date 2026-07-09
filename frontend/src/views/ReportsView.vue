<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
import { i18n } from '../i18n'
import { useCategories, categoryName } from '../composables/useCategories'
import { money, percent, fmtDate } from '../format'
import CategoryPie from '../components/CategoryPie.vue'
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
const loading = ref(false)
const err = ref<string | null>(null)

async function load() {
  loading.value = true
  err.value = null
  try {
    report.value = await api.report(refIso.value, period.value)
  } catch (e: any) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}

watch([period, monthStr, yearNum], load, { immediate: true })
watch(dataVersion, load)

const totalSpending = computed(() =>
  report.value?.breakdown.reduce((s: number, r: any) => s + r.total, 0) || 0
)

function fmtMonthLabel(m: number): string {
  return fmtDate(`${anchorYear.value}-${String(m).padStart(2, '0')}-01`, { month: 'short' })
}

function shiftYear(delta: number) {
  yearNum.value = Math.min(2100, Math.max(2000, yearNum.value + delta))
}
</script>

<template>
  <div class="switcher-row">
    <h1 style="font-size: 20px; margin: 0">{{ t('report.title') }}</h1>
    <div class="seg" role="tablist">
      <button :class="{ active: period === 'month' }" @click="period = 'month'">{{ t('report.month') }}</button>
      <button :class="{ active: period === 'year' }" @click="period = 'year'">{{ t('report.year') }}</button>
    </div>
    <input v-if="period === 'month'" type="month" v-model="monthStr" class="month-picker" />
    <div v-else class="year-spin" role="group" :aria-label="t('report.year')">
      <button class="yr-btn" type="button" aria-label="Previous year" @click="shiftYear(-1)">‹</button>
      <span class="yr-val" style="font-variant-numeric: tabular-nums">{{ yearNum }}</span>
      <button class="yr-btn" type="button" aria-label="Next year" @click="shiftYear(1)">›</button>
    </div>
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
      <CategoryPie v-if="report.breakdown.length" :rows="report.breakdown" />
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
            <td data-label="Category">{{ locale === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en }}</td>
            <td class="num" data-label="Total">{{ money(r.total) }}</td>
            <td class="num" data-label="Share" style="color: var(--ink-soft)">
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
            <td data-label="Month">{{ fmtMonthLabel(m.m) }}</td>
            <td class="num" data-label="Income" style="color: var(--accent)">{{ money(m.income) }}</td>
            <td class="num" data-label="Spending">{{ money(m.spending) }}</td>
            <td class="num" data-label="Investment">{{ money(m.investment) }}</td>
            <td class="num" data-label="Net" :style="{ color: m.net >= 0 ? 'var(--accent)' : 'var(--red)' }">
              {{ money(m.net) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.switcher-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}

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
.month-picker {
  width: auto; padding: 6px 10px; border: 1px solid var(--line);
  border-radius: 8px; background: var(--surface); font-size: 14px;
  min-width: 0;
  -webkit-appearance: none; appearance: none;
}
.month-picker::-webkit-date-and-time-value { text-align: left; min-height: 1.4em; }
.year-spin {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); border-radius: 8px; background: var(--surface);
  padding: 4px 6px;
}
.yr-btn {
  width: 26px; height: 26px; border-radius: 6px;
  font-size: 16px; line-height: 1; color: var(--ink-soft);
  background: var(--bg);
}
.yr-btn:hover { background: var(--accent-soft); color: var(--accent); }
.yr-val { font-size: 14px; font-weight: 600; min-width: 40px; text-align: center; }

@media (max-width: 640px) {
  .switcher-row { flex-wrap: wrap; gap: 8px; }
  .seg { order: 1; }
  .switcher-row .month-picker, .switcher-row .year-spin { order: 2; }
}
</style>