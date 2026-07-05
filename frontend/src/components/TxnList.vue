<script setup lang="ts">
import type { Txn } from '../api'
import { useI18n } from 'vue-i18n'
import { fmtDateLong } from '../format'
import TxnCard from './TxnCard.vue'

const props = defineProps<{ txns: Txn[] }>()
const { t } = useI18n()

// group by occurred_on, descending
const groups = (() => {
  const map = new Map<string, Txn[]>()
  for (const t of props.txns) {
    if (!map.has(t.occurred_on)) map.set(t.occurred_on, [])
    map.get(t.occurred_on)!.push(t)
  }
  return [...map.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1))
})()

function dayTotal(ts: Txn[]): number {
  return ts.reduce((s, t) => s + (t.kind === 'income' ? t.amount : -t.amount), 0)
}
</script>

<template>
  <div v-if="!txns.length" class="empty">{{ t('daily.noTransactions') }}</div>
  <div v-for="[day, ts] in groups" :key="day" class="day-group">
    <div class="day-head">
      <span>{{ fmtDateLong(day) }}</span>
      <span>{{ dayTotal(ts) >= 0 ? '+' : '−' }}{{ Math.abs(dayTotal(ts) / 100).toFixed(2) }}</span>
    </div>
    <TxnCard v-for="t in ts" :key="t.id" :txn="t" />
  </div>
</template>
