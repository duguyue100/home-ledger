<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { i18n } from '../i18n'
import { useCategories, categoryName } from '../composables/useCategories'
import { bumpData, dataVersion } from '../composables/useDataVersion'
import { money, fmtDate } from '../format'
import { watch } from 'vue'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))
const { categories, reload } = useCategories()

const today = () => new Date().toISOString().slice(0, 10)

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
  if (!confirm('Expire this category (keep history)?')) return
  await api.patchCategory(id, { valid_to: today() })
  reload(); bumpData()
}

// ---- recurring ----
const recurring = ref<any[]>([])
async function loadRecurring() { recurring.value = await api.recurring() }
loadRecurring()
watch(dataVersion, loadRecurring)

const matErr = ref<string | null>(null)
async function materialize(id: number) {
  matErr.value = null
  try { await api.materialize(id, today()); bumpData() }
  catch (e: any) { matErr.value = e.message }
}

const rKind = ref<'spending' | 'income' | 'investment'>('spending')
const rCatId = ref<number | null>(null)
const rAmount = ref('')
const rDom = ref(1)
const rNote = ref('')
const rValidFrom = ref(today())
const rErr = ref<string | null>(null)

async function addRecurring() {
  rErr.value = null
  const a = parseFloat(rAmount.value)
  if (isNaN(a)) { rErr.value = 'amount required'; return }
  if (rKind.value !== 'income' && !rCatId.value) { rErr.value = 'category required'; return }
  try {
    await api.createRecurring({
      kind: rKind.value,
      category_id: rKind.value === 'income' ? null : rCatId.value,
      amount: Math.round(a * 100),
      day_of_month: rDom.value,
      valid_from: rValidFrom.value,
      note_en: rNote.value || null,
    })
    rAmount.value = ''; rNote.value = ''; rValidFrom.value = today()
    loadRecurring(); bumpData()
  } catch (e: any) { rErr.value = e.message }
}
</script>

<template>
  <h1 style="font-size:20px;margin-bottom:16px">{{ t('settings.title') }}</h1>

  <div class="card">
    <div class="section-title">{{ t('settings.categories') }}</div>
    <table class="data-table" v-if="categories.length">
      <thead>
        <tr>
          <th>{{ t('report.category') }}</th>
          <th style="width:1%">{{ t('settings.period') }}</th>
          <th style="width:1%">{{ t('settings.validFrom') }}</th>
          <th class="action no-print">{{ t('settings.expire') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in categories" :key="c.id">
          <td data-label="Name">{{ categoryName(c, locale as string) }}</td>
          <td class="muted" data-label="Period">{{ t(`settings.${c.budget_period}`) }}</td>
          <td class="muted" data-label="Valid from" style="font-variant-numeric:tabular-nums">{{ fmtDate(c.valid_from, { year: 'numeric' }) }}</td>
          <td class="action no-print" data-label="">
            <button class="btn secondary" style="font-size:12px;padding:4px 10px"
                    @click="expireCategory(c.id)">{{ t('settings.expire') }}</button>
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
      <div class="full"><button class="btn" @click="addCategory">{{ t('daily.save') }}</button>
        <span class="err" v-if="cErr" style="margin-left:8px">{{ cErr }}</span></div>
    </div>
  </div>

  <div class="card" style="margin-top:16px">
    <div class="section-title">{{ t('settings.recurring') }}</div>
    <table class="data-table" v-if="recurring.length">
      <thead>
        <tr>
          <th>{{ t('daily.note') }}</th>
          <th style="width:1%">{{ t('daily.kind') }}</th>
          <th class="num" style="width:1%">day</th>
          <th class="num" style="width:1%">{{ t('daily.amount') }}</th>
          <th class="action no-print">{{ t('settings.materialize') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in recurring" :key="r.id">
          <td data-label="Note">{{ r.note_en || t(`kind.${r.kind}`) }}</td>
          <td class="muted" data-label="Type">{{ t(`kind.${r.kind}`) }}</td>
          <td class="num" data-label="Day" style="font-variant-numeric:tabular-nums">{{ r.day_of_month }}</td>
          <td class="num" data-label="Amount" style="font-variant-numeric:tabular-nums">{{ money(r.amount) }}</td>
          <td class="action no-print" data-label="">
            <button class="btn" style="font-size:12px;padding:4px 12px"
                    @click="materialize(r.id)">{{ t('settings.materialize') }}</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">{{ t('settings.noRecurring') }}</div>
    <div v-if="matErr" class="err" style="margin-top:8px">{{ matErr }}</div>

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
      <div><label>Day of month</label><input type="number" min="1" max="28" v-model.number="rDom" /></div>
      <div class="full"><label>{{ t('daily.note') }}</label><input v-model="rNote" /></div>
      <div><label>{{ t('settings.validFrom') }}</label><input type="date" v-model="rValidFrom" /></div>
      <div class="full"><button class="btn" @click="addRecurring">{{ t('daily.save') }}</button>
        <span class="err" v-if="rErr" style="margin-left:8px">{{ rErr }}</span></div>
    </div>
  </div>
</template>