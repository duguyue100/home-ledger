<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { useCategories, categoryName } from '../composables/useCategories'
import { bumpData } from '../composables/useDataVersion'
import { i18n } from '../i18n'
import { money } from '../format'

const { t } = useI18n()
const { categories } = useCategories()

const today = () => new Date().toISOString().slice(0, 10)
const date = ref(today())
const kind = ref<'spending' | 'income' | 'investment' | 'borrowing'>('spending')
const categoryId = ref<number | null>(null)
const amount = ref<string>('')        // CHF major units
const foreign = ref(false)
const origAmount = ref<string>('')    // foreign major units
const origCurrency = ref('CNY')
const rate = ref<string>('')          // CHF per 1 foreign major
const note = ref('')
const tag = ref('')
const saving = ref(false)
const error = ref<string | null>(null)

const computedChf = computed<number | null>(() => {
  const o = parseFloat(origAmount.value)
  const r = parseFloat(rate.value)
  if (!foreign.value || isNaN(o) || isNaN(r)) return null
  // both currencies 100 minor/major -> chf_minor = round(o_minor * rate)
  return Math.round(o * 100 * r)
})

const submitAmountMinor = computed<number | null>(() => {
  if (foreign.value) return computedChf.value
  const a = parseFloat(amount.value)
  return isNaN(a) ? null : Math.round(a * 100)
})

async function submit() {
  error.value = null
  const amt = submitAmountMinor.value
  if (amt == null) { error.value = 'amount required'; return }
  if (kind.value !== 'income' && !categoryId.value) { error.value = 'category required'; return }
  saving.value = true
  try {
    await api.createTxn({
      occurred_on: date.value,
      kind: kind.value,
      category_id: categoryId.value,
      amount: amt,
      currency: 'CHF',
      original_amount: foreign.value ? Math.round(parseFloat(origAmount.value) * 100) : null,
      original_currency: foreign.value ? origCurrency.value : null,
      note: note.value || null,
      tag: tag.value || null,
    })
    // reset
    amount.value = ''; origAmount.value = ''; rate.value = ''
    note.value = ''; tag.value = ''; foreign.value = false
    bumpData()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="card">
    <div class="section-title">{{ t('daily.quickAdd') }}</div>
    <form @submit.prevent="submit">
      <div class="grid">
        <div>
          <label>{{ t('daily.date') }}</label>
          <input type="date" v-model="date" />
        </div>
        <div>
          <label>{{ t('daily.kind') }}</label>
          <select v-model="kind">
            <option value="spending">{{ t('kind.spending') }}</option>
            <option value="income">{{ t('kind.income') }}</option>
            <option value="investment">{{ t('kind.investment') }}</option>
            <option value="borrowing">{{ t('kind.borrowing') }}</option>
          </select>
        </div>
        <div v-if="kind !== 'income'">
          <label>{{ t('daily.category') }}</label>
          <select v-model="categoryId">
            <option :value="null">—</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">
              {{ categoryName(c, i18n.global.locale.value as string) }}
            </option>
          </select>
        </div>
        <div>
          <label>{{ t('daily.amount') }} (CHF)</label>
          <input type="number" step="0.05" min="0" v-model="amount" :disabled="foreign" />
        </div>
        <div class="full">
          <label>
            <input type="checkbox" v-model="foreign" style="width:auto;margin-right:6px" />
            {{ t('daily.foreign') }}
          </label>
        </div>
        <template v-if="foreign">
          <div>
            <label>{{ t('daily.originalAmount') }}</label>
            <input type="number" step="0.01" min="0" v-model="origAmount" />
          </div>
          <div>
            <label>{{ t('daily.currency') }}</label>
            <input v-model="origCurrency" placeholder="CNY" />
          </div>
          <div>
            <label>{{ t('daily.rate') }}</label>
            <input type="number" step="0.0001" min="0" v-model="rate" />
          </div>
          <div>
            <label>= CHF</label>
            <div class="muted" style="padding-top:10px">{{ money(computedChf) }}</div>
          </div>
        </template>
        <div class="full">
          <label>{{ t('daily.note') }}</label>
          <input v-model="note" />
        </div>
        <div class="full">
          <label>{{ t('daily.tag') }}</label>
          <input v-model="tag" placeholder="trip:china-2026" />
        </div>
        <div class="full row" style="gap:8px">
          <button class="btn" :disabled="saving">{{ t('daily.save') }}</button>
          <span class="err" v-if="error">{{ error }}</span>
        </div>
      </div>
    </form>
  </div>
</template>
