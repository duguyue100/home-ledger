<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { api, type Txn } from '../api'
import { i18n } from '../i18n'
import { findCategory, categoryName } from '../composables/useCategories'
import { bumpData } from '../composables/useDataVersion'
import { money, fmtDate } from '../format'

const props = defineProps<{ txn: Txn }>()
const { t } = useI18n()

async function del() {
  if (!confirm(`Delete ${money(props.txn.amount)} (${fmtDate(props.txn.occurred_on)})?`)) return
  await api.deleteTxn(props.txn.id)
  bumpData()
}
</script>

<template>
  <div class="txn-card">
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
    <button class="del" @click="del">✕</button>
  </div>
</template>
