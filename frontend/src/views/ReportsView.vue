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

function signedPct(p: number | null | undefined): string {
  if (p == null) return t('report.deltas.noData')
  const s = p >= 0 ? '+' : ''
  return `${s}${(p * 100).toFixed(1)}%`
}
function pctColor(p: number | null | undefined, invert = false): string {
  if (p == null) return 'var(--ink-soft)'
  // invert=true for spending (down is good → accent); default for income/net (up is good)
  const good = invert ? p < 0 : p > 0
  return good ? 'var(--accent)' : 'var(--red)'
}
function volTone(cv: number): string {
  if (cv < 0.15) return t('report.volatility.stable')
  if (cv < 0.30) return t('report.volatility.moderate')
  return t('report.volatility.variable')
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

    <!-- summary tiles with delta badges -->
    <div class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.summary') }}</div>
      <div class="tiles" style="margin-top: 8px">
        <div class="tile">
          <div class="label">{{ t('kind.income') }}</div>
          <div class="value" style="color: var(--accent)">{{ money(report.summary.income) }}</div>
          <div class="delta" v-if="period === 'month' && report.deltas?.has_mom">
            {{ signedPct(report.deltas.mom.income) }} {{ t('report.deltas.vs') }} {{ t('report.deltas.mom') }}
          </div>
          <div class="delta" v-if="period === 'month' && report.deltas?.has_yoy">
            {{ signedPct(report.deltas.yoy.income) }} {{ t('report.deltas.vs') }} {{ t('report.deltas.yoy') }}
          </div>
        </div>
        <div class="tile">
          <div class="label">{{ t('kind.spending') }}</div>
          <div class="value">{{ money(report.summary.spending) }}</div>
          <div class="delta" v-if="period === 'month' && report.deltas?.has_mom"
               :style="{ color: pctColor(report.deltas.mom.spending, true) }">
            {{ signedPct(report.deltas.mom.spending) }} {{ t('report.deltas.vs') }} {{ t('report.deltas.mom') }}
          </div>
          <div class="delta" v-if="period === 'month' && report.deltas?.has_yoy"
               :style="{ color: pctColor(report.deltas.yoy.spending, true) }">
            {{ signedPct(report.deltas.yoy.spending) }} {{ t('report.deltas.vs') }} {{ t('report.deltas.yoy') }}
          </div>
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
          <div class="delta" v-if="period === 'month' && report.deltas?.has_mom"
               :style="{ color: pctColor(report.deltas.mom.net) }">
            {{ signedPct(report.deltas.mom.net) }} {{ t('report.deltas.vs') }} {{ t('report.deltas.mom') }}
          </div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsRate') }}</div>
          <div class="value">{{ percent(report.savings_rate) }}</div>
        </div>
      </div>
    </div>

    <!-- savings rate benchmarks (monthly only — yearly uses anchors differently) -->
    <div v-if="period === 'month' && report.savings_rate_stats" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.savingsBenchmarks.title') }}</div>
      <div class="card-desc">{{ t('report.savingsBenchmarks.desc') }}</div>
      <div class="tiles" style="margin-top: 8px">
        <div class="tile">
          <div class="label">{{ t('report.savingsBenchmarks.current') }}</div>
          <div class="value" style="color: var(--accent)">{{ percent(report.savings_rate_stats.current) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsBenchmarks.median') }}</div>
          <div class="value">{{ percent(report.savings_rate_stats.median) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsBenchmarks.best') }}</div>
          <div class="value" style="color: var(--accent)">{{ percent(report.savings_rate_stats.best) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsBenchmarks.worst') }}</div>
          <div class="value" style="color: var(--red)">{{ percent(report.savings_rate_stats.worst) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.savingsBenchmarks.monthsAbove') }}</div>
          <div class="value">{{ report.savings_rate_stats.months_above_target }} / {{ report.savings_rate_stats.months_with_data }}</div>
        </div>
      </div>
    </div>

    <!-- fixed vs discretionary -->
    <div v-if="report.fixed_discretionary" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.fixedVsDisc.title') }}</div>
      <div class="card-desc">{{ t('report.fixedVsDisc.desc') }}</div>
      <div style="margin-top: 12px">
        <div class="stack-bar">
          <div class="seg-fixed" :style="{ width: (report.fixed_discretionary.fixed_pct * 100) + '%' }"></div>
          <div class="seg-disc" :style="{ width: (report.fixed_discretionary.disc_pct * 100) + '%' }"></div>
        </div>
        <div class="stack-legend" style="margin-top: 8px">
          <span><span class="dot fixed"></span>{{ t('report.fixedVsDisc.fixed') }} {{ money(report.fixed_discretionary.fixed) }} ({{ percent(report.fixed_discretionary.fixed_pct) }})</span>
          <span><span class="dot disc"></span>{{ t('report.fixedVsDisc.discretionary') }} {{ money(report.fixed_discretionary.discretionary) }} ({{ percent(report.fixed_discretionary.disc_pct) }})</span>
        </div>
      </div>
    </div>

    <!-- spending volatility -->
    <div v-if="report.volatility" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.volatility.title') }}</div>
      <div class="card-desc">{{ t('report.volatility.desc') }}</div>
      <div class="tiles" style="margin-top: 8px">
        <div class="tile">
          <div class="label">{{ t('report.volatility.avgMonthly') }}</div>
          <div class="value">{{ money(report.volatility.mean) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.volatility.stdDev') }}</div>
          <div class="value">{{ money(report.volatility.std) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.volatility.cv') }}</div>
          <div class="value" :style="{ color: report.volatility.cv < 0.15 ? 'var(--accent)' : report.volatility.cv < 0.30 ? 'var(--ink)' : 'var(--red)' }">
            {{ percent(report.volatility.cv) }}
          </div>
          <div class="delta">{{ volTone(report.volatility.cv) }}</div>
        </div>
        <div class="tile">
          <div class="label">{{ t('report.volatility.range') }}</div>
          <div class="value" style="font-size: 16px">{{ money(report.volatility.min) }} – {{ money(report.volatility.max) }}</div>
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

    <!-- subscription audit -->
    <div v-if="report.recurring_audit" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.subscriptions.title') }}</div>
      <div class="card-desc">{{ t('report.subscriptions.desc') }}</div>
      <div style="margin-top: 10px; font-size: 22px; font-weight: 600; color: var(--accent)">
        {{ money(report.recurring_audit.total_annual) }}
        <span style="font-size: 13px; font-weight: 400; color: var(--ink-soft)">
          {{ t('report.subscriptions.totalYear', { n: report.recurring_audit.count }) }}
        </span>
      </div>
      <table v-if="report.recurring_audit.items.length" class="data-table" style="margin-top: 10px">
        <thead>
          <tr>
            <th>{{ t('report.subscriptions.name') }}</th>
            <th class="num">{{ t('report.subscriptions.monthly') }}</th>
            <th class="num">{{ t('report.subscriptions.annual') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in report.recurring_audit.items" :key="i.id">
            <td data-label="Name">{{ i.note }}</td>
            <td class="num" data-label="Monthly">{{ money(i.monthly) }}</td>
            <td class="num" data-label="Annual">{{ money(i.annual) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- tagged spending -->
    <div v-if="report.tag_breakdown?.length" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.tags.title') }}</div>
      <div class="card-desc">{{ t('report.tags.desc') }}</div>
      <table class="data-table" style="margin-top: 10px">
        <thead>
          <tr>
            <th>{{ t('report.tags.tag') }}</th>
            <th class="num">{{ t('report.tags.total') }}</th>
            <th class="num">{{ t('report.tags.count') }}</th>
            <th class="num">{{ t('report.tags.share') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in report.tag_breakdown" :key="r.tag">
            <td data-label="Tag">{{ r.tag }}</td>
            <td class="num" data-label="Total">{{ money(r.total) }}</td>
            <td class="num" data-label="Count">{{ r.count }}</td>
            <td class="num" data-label="Share" style="color: var(--ink-soft)">
              {{ totalSpending ? percent(r.total / totalSpending) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- YTD projection (yearly mode only) -->
    <div v-if="period === 'year' && report.ytd_projection" class="card" style="margin-top: 16px">
      <div class="section-title">{{ t('report.projection.title') }}</div>
      <div class="card-desc">{{ t('report.projection.desc') }}</div>
      <div style="margin-top: 10px; display: flex; gap: 20px; flex-wrap: wrap; align-items: baseline">
        <div>
          <div style="font-size: 11px; color: var(--ink-soft)">{{ t('report.projection.projectedYear') }}</div>
          <div style="font-size: 22px; font-weight: 600; color: var(--accent)">{{ money(report.ytd_projection.projected_annual) }}</div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--ink-soft)">{{ t('report.projection.spentYtd') }}</div>
          <div style="font-size: 16px; font-weight: 600">{{ money(report.ytd_projection.spent_ytd) }}</div>
        </div>
        <div>
          <div style="font-size: 11px; color: var(--ink-soft)">{{ t('report.projection.monthsElapsed', { n: report.ytd_projection.months_elapsed }) }}</div>
        </div>
      </div>
      <table v-if="report.ytd_projection.by_category.length" class="data-table" style="margin-top: 12px">
        <thead>
          <tr>
            <th>{{ t('report.projection.category') }}</th>
            <th class="num">{{ t('report.projection.projected') }}</th>
            <th class="num">{{ t('report.projection.budget') }}</th>
            <th>{{ t('report.projection.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in report.ytd_projection.by_category" :key="c.name_en">
            <td data-label="Category">{{ locale === 'zh-CN' && c.name_zh ? c.name_zh : c.name_en }}</td>
            <td class="num" data-label="Projected">{{ money(c.projected) }}</td>
            <td class="num" data-label="Budget">{{ money(c.budget) }}</td>
            <td data-label="Status">
              <span class="pill" :class="{
                active: c.status === 'on-track',
                'expired': c.status !== 'on-track'
              }" :style="{
                background: c.status === 'on-track' ? 'var(--accent)' : c.status === 'at-risk' ? '#d97706' : 'var(--red)',
                color: '#fff'
              }">
                {{ t(`report.projection.${c.status === 'on-track' ? 'onTrack' : c.status === 'at-risk' ? 'atRisk' : c.status}`) }}
              </span>
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

/* enrichment cards */
.card-desc {
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.45;
  margin-top: 2px;
  font-style: italic;
}
.delta {
  font-size: 11px;
  color: var(--ink-soft);
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}
.stack-bar {
  display: flex;
  height: 14px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg);
}
.seg-fixed { background: var(--accent); }
.seg-disc { background: #94a3b8; }
.stack-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
}
.stack-legend .dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: middle;
}
.dot.fixed { background: var(--accent); }
.dot.disc { background: #94a3b8; }
</style>