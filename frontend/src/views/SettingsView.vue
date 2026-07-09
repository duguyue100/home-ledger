<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type Budget } from '../api'
import { i18n } from '../i18n'
import { useCategories, categoryName } from '../composables/useCategories'
import { bumpData, dataVersion } from '../composables/useDataVersion'
import { money, fmtDate } from '../format'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))
const { categories, allCategories, reload } = useCategories()

const today = () => new Date().toISOString().slice(0, 10)
function isExpired(row: { valid_to: string | null }): boolean {
  return row.valid_to != null && row.valid_to <= today()
}

// all budgets → map category_id → active amount (most recent active)
const budgets = ref<Budget[]>([])
async function loadBudgets() { budgets.value = await api.allBudgets() }
loadBudgets()
watch(dataVersion, loadBudgets)

const budgetByCat = computed(() => {
  const m = new Map<number, number | null>()
  const todayStr = today()
  for (const c of allCategories.value) {
    const bs = budgets.value
      .filter((b) => b.category_id === c.id)
      .filter((b) => b.valid_to == null || b.valid_to > todayStr)
      .sort((a, b) => a.valid_from.localeCompare(b.valid_from))
    const last = bs[bs.length - 1]
    m.set(c.id, last && c.budget_period !== 'none' ? last.amount : null)
  }
  return m
})

// ---- add category ----
const cNameEn = ref('')
const cNameZh = ref('')
const cPeriod = ref<'monthly' | 'yearly' | 'none'>('monthly')
const cValidFrom = ref(today())
const cBudget = ref<string>('')
const cErr = ref<string | null>(null)

async function addCategory() {
  cErr.value = null
  if (!cNameEn.value) { cErr.value = 'name required'; return }
  try {
    const c = await api.createCategory({
      name_en: cNameEn.value, name_zh: cNameZh.value || null,
      budget_period: cPeriod.value, valid_from: cValidFrom.value,
    })
    const b = parseFloat(cBudget.value)
    if (!isNaN(b) && b > 0) {
      await api.createBudget({
        category_id: c.id, amount: Math.round(b * 100), valid_from: cValidFrom.value,
      })
    }
    cNameEn.value = ''; cNameZh.value = ''; cBudget.value = ''; cValidFrom.value = today()
    reload(); bumpData()
  } catch (e: any) { cErr.value = e.message }
}

async function expireCategory(id: number) {
  if (!confirm(t('settings.expire') + '?')) return
  await api.patchCategory(id, { valid_to: today() })
  reload(); bumpData()
}

async function toggleFixed(id: number, val: boolean) {
  await api.patchCategory(id, { is_fixed: val })
  reload(); bumpData()
}

async function reviveCategory(id: number) {
  await api.reviveCategory(id)
  reload(); bumpData()
}

async function deleteCategory(id: number) {
  if (!confirm(t('settings.confirmDelete'))) return
  try {
    await api.deleteCategory(id)
    reload(); bumpData()
  } catch (e: any) { alert(e.message) }
}

// ---- recurring ----
const allRecurring = ref<any[]>([])
async function loadRecurring() { allRecurring.value = await api.allRecurring() }
loadRecurring()
watch(dataVersion, loadRecurring)

const rKind = ref<'spending' | 'income' | 'investment'>('spending')
const rCatId = ref<number | null>(null)
const rAmount = ref('')
const rNote = ref('')
const rValidFrom = ref(today())
const rErr = ref<string | null>(null)

function sameMonth(d1: string, d2: string): boolean {
  return d1.slice(0, 7) === d2.slice(0, 7)
}

async function addRecurring() {
  rErr.value = null
  const a = parseFloat(rAmount.value)
  if (isNaN(a)) { rErr.value = 'amount required'; return }
  if (rKind.value !== 'income' && !rCatId.value) { rErr.value = 'category required'; return }
  try {
    const r = await api.createRecurring({
      kind: rKind.value,
      category_id: rKind.value === 'income' ? null : rCatId.value,
      amount: Math.round(a * 100),
      day_of_month: 1,
      valid_from: rValidFrom.value,
      note_en: rNote.value || null,
    })
    // auto-post if valid_from is in the current month
    if (sameMonth(rValidFrom.value, today())) {
      try { await api.materialize(r.id, rValidFrom.value) } catch { /* already posted */ }
    }
    rAmount.value = ''; rNote.value = ''; rValidFrom.value = today()
    loadRecurring(); bumpData()
  } catch (e: any) { rErr.value = e.message }
}

async function expireRecurring(id: number) {
  if (!confirm(t('settings.expire') + '?')) return
  await api.patchRecurring(id, { valid_to: today() })
  loadRecurring(); bumpData()
}

async function reviveRecurring(id: number) {
  await api.reviveRecurring(id)
  loadRecurring(); bumpData()
}

async function deleteRecurring(id: number) {
  if (!confirm(t('settings.confirmDelete'))) return
  try {
    await api.deleteRecurring(id)
    loadRecurring(); bumpData()
  } catch (e: any) { alert(e.message) }
}

// sort: active first, then expired by valid_from desc
const sortedCats = computed(() =>
  [...allCategories.value].sort((a, b) => {
    const ae = isExpired(a) ? 1 : 0, be = isExpired(b) ? 1 : 0
    if (ae !== be) return ae - be
    return b.valid_from.localeCompare(a.valid_from)
  })
)
const sortedRecur = computed(() =>
  [...allRecurring.value].sort((a, b) => {
    const ae = isExpired(a) ? 1 : 0, be = isExpired(b) ? 1 : 0
    if (ae !== be) return ae - be
    return b.valid_from.localeCompare(a.valid_from)
  })
)
</script>

<template>
  <h1 style="font-size:20px;margin-bottom:16px">{{ t('settings.title') }}</h1>

  <div class="card">
    <div class="section-title">{{ t('settings.categories') }}</div>
    <table class="data-table" v-if="sortedCats.length">
      <thead>
        <tr>
          <th>{{ t('report.category') }}</th>
          <th>{{ t('settings.period') }}</th>
          <th class="num">{{ t('settings.budget') }}</th>
          <th>{{ t('settings.validFrom') }}</th>
          <th>{{ t('settings.validTo') }}</th>
          <th>{{ t('settings.status') }}</th>
          <th class="num">{{ t('settings.fixed') }}</th>
          <th class="action"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in sortedCats" :key="c.id" :class="{ 'row-expired': isExpired(c) }">
          <td class="name" data-label="Name">{{ categoryName(c, locale as string) }}</td>
          <td class="muted nw" data-label="Period">{{ t(`settings.${c.budget_period}`) }}</td>
          <td class="num nw" data-label="Budget">
            {{ budgetByCat.get(c.id) != null ? money(budgetByCat.get(c.id)!) : '—' }}
          </td>
          <td class="muted nw" data-label="Valid from">
            {{ fmtDate(c.valid_from, { day: 'numeric', month: 'short', year: 'numeric' }) }}
          </td>
          <td class="muted nw" data-label="Valid to">
            {{ c.valid_to ? fmtDate(c.valid_to, { day: 'numeric', month: 'short', year: 'numeric' }) : '—' }}
          </td>
          <td class="nw" data-label="Status">
            <span class="pill" :class="isExpired(c) ? 'expired' : 'active'">
              {{ isExpired(c) ? t('settings.expired') : t('settings.active') }}
            </span>
          </td>
          <td class="num" data-label="Fixed">
            <input type="checkbox" :checked="c.is_fixed"
                   @change="toggleFixed(c.id, ($event.target as HTMLInputElement).checked)"
                   style="width:auto" />
          </td>
          <td class="action" data-label="">
            <div class="row-actions">
              <button v-if="!isExpired(c)" class="btn secondary" style="font-size:12px;padding:4px 10px"
                      @click="expireCategory(c.id)">{{ t('settings.expire') }}</button>
              <button v-else class="btn ghost" style="font-size:12px;padding:4px 10px"
                      @click="reviveCategory(c.id)">{{ t('settings.revive') }}</button>
              <button class="btn ghost delete-link" style="font-size:12px;padding:4px 10px"
                      :title="t('settings.delete')"
                      @click="deleteCategory(c.id)">✕</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">{{ t('common.loading') }}</div>

    <div class="section-title" style="margin-top:20px">{{ t('settings.addCategory') }}</div>
    <div class="grid">
      <div><label>{{ t('settings.nameEn') }}</label><input v-model="cNameEn" /></div>
      <div><label>{{ t('settings.nameZh') }}</label><input v-model="cNameZh" /></div>
      <div>
        <label>{{ t('settings.period') }}</label>
        <select v-model="cPeriod">
          <option value="monthly">{{ t('settings.monthly') }}</option>
          <option value="yearly">{{ t('settings.yearly') }}</option>
          <option value="none">{{ t('settings.none') }}</option>
        </select>
      </div>
      <div><label>Initial budget (CHF)</label><input type="number" step="0.05" min="0" v-model="cBudget" /></div>
      <div><label>{{ t('settings.validFrom') }}</label><input type="date" v-model="cValidFrom" /></div>
    </div>
    <div class="form-actions">
      <button class="btn" @click="addCategory">{{ t('daily.save') }}</button>
      <span class="err" v-if="cErr">{{ cErr }}</span>
    </div>
  </div>

  <div class="card" style="margin-top:16px">
    <div class="section-title">{{ t('settings.recurring') }}</div>
    <table class="data-table" v-if="sortedRecur.length">
      <thead>
        <tr>
          <th>{{ t('daily.note') }}</th>
          <th>{{ t('daily.kind') }}</th>
          <th class="num">{{ t('daily.amount') }}</th>
          <th>{{ t('settings.validFrom') }}</th>
          <th>{{ t('settings.validTo') }}</th>
          <th>{{ t('settings.status') }}</th>
          <th class="action"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in sortedRecur" :key="r.id" :class="{ 'row-expired': isExpired(r) }">
          <td class="name" data-label="Note">{{ r.note_en || t(`kind.${r.kind}`) }}</td>
          <td class="muted nw" data-label="Type">{{ t(`kind.${r.kind}`) }}</td>
          <td class="num nw" data-label="Amount">{{ money(r.amount) }}</td>
          <td class="muted nw" data-label="Valid from">
            {{ fmtDate(r.valid_from, { day: 'numeric', month: 'short', year: 'numeric' }) }}
          </td>
          <td class="muted nw" data-label="Valid to">
            {{ r.valid_to ? fmtDate(r.valid_to, { day: 'numeric', month: 'short', year: 'numeric' }) : '—' }}
          </td>
          <td class="nw" data-label="Status">
            <span class="pill" :class="isExpired(r) ? 'expired' : 'active'">
              {{ isExpired(r) ? t('settings.expired') : t('settings.active') }}
            </span>
          </td>
          <td class="action" data-label="">
            <div class="row-actions">
              <button v-if="!isExpired(r)" class="btn secondary" style="font-size:12px;padding:4px 10px"
                      @click="expireRecurring(r.id)">{{ t('settings.expire') }}</button>
              <button v-else class="btn ghost" style="font-size:12px;padding:4px 10px"
                      @click="reviveRecurring(r.id)">{{ t('settings.revive') }}</button>
              <button class="btn ghost delete-link" style="font-size:12px;padding:4px 10px"
                      :title="t('settings.delete')"
                      @click="deleteRecurring(r.id)">✕</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">{{ t('settings.noRecurring') }}</div>

    <div class="section-title" style="margin-top:20px">Add recurring</div>
    <div class="grid">
      <div>
        <label>{{ t('daily.kind') }}</label>
        <select v-model="rKind">
          <option value="spending">{{ t('kind.spending') }}</option>
          <option value="income">{{ t('kind.income') }}</option>
          <option value="investment">{{ t('kind.investment') }}</option>
        </select>
      </div>
      <div v-if="rKind !== 'income'">
        <label>{{ t('daily.category') }}</label>
        <select v-model="rCatId">
          <option :value="null">—</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ categoryName(c, locale as string) }}</option>
        </select>
      </div>
      <div><label>{{ t('daily.amount') }} (CHF)</label><input type="number" step="0.05" min="0" v-model="rAmount" /></div>
      <div><label>{{ t('settings.validFrom') }}</label><input type="date" v-model="rValidFrom" /></div>
      <div class="full"><label>{{ t('daily.note') }}</label><input v-model="rNote" /></div>
    </div>
    <div class="form-actions">
      <button class="btn" @click="addRecurring">{{ t('daily.save') }}</button>
      <span class="err" v-if="rErr">{{ rErr }}</span>
    </div>
  </div>
</template>

<style scoped>
.row-expired td { opacity: 0.55; }
.row-actions { display: inline-flex; gap: 6px; align-items: center; }
.delete-link { color: var(--ink-soft); }
.delete-link:hover { color: var(--red); border-color: var(--red); }
</style>