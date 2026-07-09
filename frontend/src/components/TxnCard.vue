<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type Txn } from '../api'
import { i18n } from '../i18n'
import { useCategories, findCategory, categoryName } from '../composables/useCategories'
import { bumpData } from '../composables/useDataVersion'
import { money, fmtDate } from '../format'

const props = defineProps<{ txn: Txn }>()
const { t } = useI18n()
const { categories } = useCategories()

const editing = ref(false)

// form state
const fDate = ref(props.txn.occurred_on)
const fKind = ref(props.txn.kind)
const fCat = ref<number | null>(props.txn.category_id)
const fAmount = ref((props.txn.amount / 100).toFixed(2))
const fNote = ref(props.txn.note || '')
const fTag = ref(props.txn.tag || '')
const saving = ref(false)
const err = ref<string | null>(null)

function startEdit() {
  fDate.value = props.txn.occurred_on
  fKind.value = props.txn.kind
  fCat.value = props.txn.category_id
  fAmount.value = (props.txn.amount / 100).toFixed(2)
  fNote.value = props.txn.note || ''
  fTag.value = props.txn.tag || ''
  err.value = null
  editing.value = true
}

function cancelEdit() { editing.value = false; err.value = null }

async function saveEdit() {
  err.value = null
  const amt = parseFloat(fAmount.value)
  if (isNaN(amt)) { err.value = 'amount required'; return }
  if (fKind.value !== 'income' && !fCat.value) { err.value = 'category required'; return }
  saving.value = true
  try {
    await api.patchTxn(props.txn.id, {
      occurred_on: fDate.value,
      kind: fKind.value,
      category_id: fCat.value,
      amount: Math.round(amt * 100),
      note: fNote.value || null,
      tag: fTag.value || null,
    })
    editing.value = false
    bumpData()
  } catch (e: any) {
    err.value = e.message
  } finally {
    saving.value = false
  }
}

async function del() {
  if (!confirm(`Delete ${money(props.txn.amount)} (${fmtDate(props.txn.occurred_on)})?`)) return
  await api.deleteTxn(props.txn.id)
  bumpData()
}
</script>

<template>
  <div class="txn-card" :class="{ editing }">
    <!-- view mode -->
    <template v-if="!editing">
      <span class="kind-dot" :class="txn.kind"></span>
      <div>
        <div class="note">{{ txn.note || t(`kind.${txn.kind}`) }}</div>
        <div class="cat">
          {{ categoryName(findCategory(txn.category_id), i18n.global.locale.value as string) }}
          <span class="tag" v-if="txn.tag">{{ txn.tag }}</span>
          <span class="muted" v-if="txn.original_currency">
            · {{ (txn.original_amount! / 100).toFixed(2) }} {{ txn.original_currency }}
          </span>
        </div>
      </div>
      <div class="amount" :class="txn.kind">
        {{ txn.kind === 'income' ? '+' : txn.kind === 'spending' || txn.kind === 'borrowing' ? '−' : '' }}{{ money(txn.amount) }}
      </div>
      <button class="del" @click="startEdit" :title="t('daily.save')">✎</button>
      <button class="del" @click="del">✕</button>
    </template>

    <!-- edit mode -->
    <template v-else>
      <div class="edit-form">
        <div class="edit-row">
          <label>{{ t('daily.date') }}<input type="date" v-model="fDate" /></label>
          <label>{{ t('daily.kind') }}
            <select v-model="fKind">
              <option value="spending">{{ t('kind.spending') }}</option>
              <option value="income">{{ t('kind.income') }}</option>
              <option value="investment">{{ t('kind.investment') }}</option>
              <option value="borrowing">{{ t('kind.borrowing') }}</option>
            </select>
          </label>
          <label v-if="fKind !== 'income'">{{ t('daily.category') }}
            <select v-model="fCat">
              <option :value="null">—</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">
                {{ categoryName(c, i18n.global.locale.value as string) }}
              </option>
            </select>
          </label>
          <label>{{ t('daily.amount') }} (CHF)<input type="number" step="0.05" min="0" v-model="fAmount" /></label>
        </div>
        <div class="edit-row">
          <label class="full">{{ t('daily.note') }}<input v-model="fNote" /></label>
        </div>
        <div class="edit-row">
          <label class="full">{{ t('daily.tag') }}<input v-model="fTag" placeholder="trip:china-2026" /></label>
        </div>
        <div class="edit-actions">
          <button class="btn" :disabled="saving" @click="saveEdit">{{ t('daily.save') }}</button>
          <button class="btn secondary" @click="cancelEdit">{{ t('daily.cancel') }}</button>
          <span class="err" v-if="err">{{ err }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.txn-card.editing { display: block; padding: 12px; }
.edit-form { display: flex; flex-direction: column; gap: 8px; }
.edit-row { display: flex; gap: 8px; flex-wrap: wrap; }
.edit-row label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--ink-soft); flex: 1; min-width: 120px; }
.edit-row label.full { flex-basis: 100%; }
.edit-row input, .edit-row select { font-size: 14px; padding: 5px 8px; }
.edit-actions { display: flex; align-items: center; gap: 8px; }
.edit-actions .btn { padding: 5px 14px; font-size: 13px; }
</style>