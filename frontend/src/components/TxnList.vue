<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Txn } from '../api'
import { useI18n } from 'vue-i18n'
import { i18n } from '../i18n'
import { fmtDateLong } from '../format'
import { findCategory, categoryName } from '../composables/useCategories'
import TxnCard from './TxnCard.vue'

const props = defineProps<{ txns: Txn[] }>()
const { t } = useI18n()

type SortKey = 'date' | 'amount' | 'category' | 'kind'
const DEFAULT: { key: SortKey; asc: boolean } = { key: 'date', asc: false }
const sort = ref<{ key: SortKey; asc: boolean }>({ ...DEFAULT })

function setSort(key: SortKey) {
  if (sort.value.key === key) {
    // toggle direction
    sort.value = { key, asc: !sort.value.asc }
    return
  }
  // sensible default per key
  const ascDefault = key === 'date' || key === 'amount' ? false : true
  sort.value = { key, asc: ascDefault }
}

function resetSort() { sort.value = { ...DEFAULT } }

function cmpDate(a: Txn, b: Txn) {
  if (a.occurred_on !== b.occurred_on) return a.occurred_on < b.occurred_on ? -1 : 1
  return a.id - b.id
}
function cmpAmount(a: Txn, b: Txn) { return a.amount - b.amount }
function cmpKind(a: Txn, b: Txn) { return a.kind < b.kind ? -1 : a.kind > b.kind ? 1 : 0 }
function cmpCategory(a: Txn, b: Txn) {
  const ca = findCategory(a.category_id)?.name_en ?? ''
  const cb = findCategory(b.category_id)?.name_en ?? ''
  if (ca !== cb) return ca < cb ? -1 : 1
  return cmpDate(a, b)
}

const sorted = computed<Txn[]>(() => {
  const arr = [...props.txns]
  const { key, asc } = sort.value
  let fn: (a: Txn, b: Txn) => number
  if (key === 'amount') fn = cmpAmount
  else if (key === 'kind') fn = cmpKind
  else if (key === 'category') fn = cmpCategory
  else fn = cmpDate
  arr.sort(fn)
  return asc ? arr : arr.reverse()
})

// day-group only when sorting by date desc (default view)
const grouped = computed(() => {
  if (sort.value.key !== 'date' || sort.value.asc) return null
  const map = new Map<string, Txn[]>()
  for (const t of sorted.value) {
    if (!map.has(t.occurred_on)) map.set(t.occurred_on, [])
    map.get(t.occurred_on)!.push(t)
  }
  return [...map.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1))
})

function dayTotal(ts: Txn[]): number {
  return ts.reduce((s, t) => s + (t.kind === 'income' ? t.amount : -t.amount), 0)
}

const ARROW = { asc: '↑', desc: '↓' } as const
function icon(k: SortKey): string | null {
  if (sort.value.key !== k) return null
  return sort.value.asc ? ARROW.asc : ARROW.desc
}
</script>

<template>
  <div v-if="!txns.length" class="empty">{{ t('daily.noTransactions') }}</div>
  <div v-else>
    <div class="sort-row">
      <span class="sort-label">{{ t('daily.sortBy') }}</span>
      <button
        v-for="k in (['date','amount','category','kind'] as SortKey[])"
        :key="k"
        class="sort-pill"
        :class="{ active: sort.key === k }"
        @click="setSort(k)"
      >
        {{ t(`daily.sort.${k}`) }}<span class="sort-icon" v-if="icon(k)">{{ icon(k) }}</span>
      </button>
      <button class="sort-reset" @click="resetSort" :title="t('daily.sort.reset')" aria-label="Reset sort">↺</button>
    </div>

    <!-- grouped (default: date desc) -->
    <div v-if="grouped" v-for="[day, ts] in grouped" :key="day" class="day-group">
      <div class="day-head">
        <span>{{ fmtDateLong(day) }}</span>
        <span>{{ dayTotal(ts) >= 0 ? '+' : '−' }}{{ Math.abs(dayTotal(ts) / 100).toFixed(2) }}</span>
      </div>
      <TxnCard v-for="t in ts" :key="t.id" :txn="t" />
    </div>

    <!-- flat: non-date sort -->
    <div v-else>
      <TxnCard v-for="t in sorted" :key="t.id" :txn="t" />
    </div>
  </div>
</template>

<style scoped>
.sort-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
  padding: 8px 0;
  margin-bottom: 4px;
  font-size: 12px;
  border-bottom: 1px solid var(--line);
}
.sort-label { color: var(--ink-soft); margin-right: 4px; white-space: nowrap; }
.sort-pill {
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--ink);
  padding: 3px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background .12s, color .12s, border-color .12s;
}
.sort-pill:hover { border-color: var(--accent); color: var(--accent); }
.sort-pill.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.sort-icon { font-weight: 600; }
.sort-reset {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}
.sort-reset:hover { color: var(--accent); background: var(--surface); }
.flat-head { font-size: 12px; color: var(--ink-soft); font-weight: 400; justify-content: space-between; }
.flat-head .count { font-variant-numeric: tabular-nums; }
</style>