<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { i18n } from '../i18n'
import { useCategories, categoryName, findCategory } from '../composables/useCategories'
import { money, percent, fmtDate } from '../format'
import { useTransactions } from '../composables/useTransactions'
import QuickAdd from '../components/QuickAdd.vue'
import TxnList from '../components/TxnList.vue'

const { t } = useI18n()
const locale = computed(() => (i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'))
const { categories } = useCategories()

// ---- filters ----
const showFilters = ref(false)
const kinds = ref<Record<string, boolean>>({ spending: true, income: true, investment: false, borrowing: false })
const categoryId = ref<number | null>(null)
const tag = ref('')
const q = ref('')
const days = ref(10)

function isoDaysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return iso(d)
}
function iso(d: Date): string { return d.toISOString().slice(0, 10) }

const selectedKinds = computed(() =>
  Object.entries(kinds.value).filter(([, v]) => v).map(([k]) => k)
)

const { items, loading, error } = useTransactions(() => ({
  from: isoDaysAgo(days.value - 1),
  to: isoDaysAgo(-1),
  kind: selectedKinds.value.length ? selectedKinds.value : undefined,
  category_id: categoryId.value ?? undefined,
  tag: tag.value || undefined,
  q: q.value || undefined,
  limit: 1000,
}))

watch(() => i18n.global.locale.value, () => {}) // re-render label names

function toggleFilters() { showFilters.value = !showFilters.value }
function applyFilters() { showFilters.value = false }
function resetFilters() {
  kinds.value = { spending: true, income: true, investment: false, borrowing: false }
  categoryId.value = null
  tag.value = ''
  q.value = ''
  days.value = 10
}
</script>

<template>
  <h1 style="font-size:20px;display:flex;align-items:center;flex-wrap:wrap;gap:8px 10px;margin-bottom:0">
    {{ t('daily.title') }}
    <span class="muted" style="font-size:13px;font-weight:400">
      {{ t('daily.lastDays', { n: days }) }}
    </span>
    <button
      class="btn secondary no-print filter-toggle"
      :class="{ active: showFilters }"
      style="margin-left:auto;font-size:13px;padding:5px 12px;display:inline-flex;align-items:center;gap:6px"
      @click="toggleFilters">
      <span :style="{ transform: showFilters ? 'rotate(90deg)' : 'none', display: 'inline-block', transition: 'transform .12s' }">▸</span>
      {{ showFilters ? t('daily.hideFilters') : t('daily.showFilters') }}
    </button>
  </h1>

  <div v-if="showFilters" class="filters-strip no-print">
    <div class="grid">
      <div>
        <label>{{ t('daily.kind') }}</label>
        <div style="display:flex;flex-wrap:wrap;gap:8px;padding-top:4px">
          <label v-for="k in ['spending','income','investment','borrowing']" :key="k" style="display:flex;align-items:center;gap:6px;margin:0;font-size:13px;color:var(--ink)">
            <input type="checkbox" v-model="kinds[k]" style="width:auto" />
            {{ t(`kind.${k}`) }}
          </label>
        </div>
      </div>
      <div>
        <label>{{ t('daily.category') }}</label>
        <select v-model="categoryId">
          <option :value="null">— {{ t('daily.all') }} —</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">
            {{ categoryName(c, locale as string) }}
          </option>
        </select>
      </div>
      <div>
        <label>{{ t('daily.tag') }}</label>
        <input v-model="tag" placeholder="trip:china-2026" />
      </div>
      <div>
        <label>{{ t('daily.noteSearch') }}</label>
        <input v-model="q" />
      </div>
      <div>
        <label>{{ t('daily.windowDays') }}</label>
        <input type="number" min="1" max="120" v-model.number="days" />
      </div>
      <div class="full" style="display:flex;gap:8px;align-items:flex-end">
        <button class="btn" style="padding:7px 14px;font-size:13px" @click="applyFilters">{{ t('daily.apply') }}</button>
        <button class="btn secondary" style="padding:7px 14px;font-size:13px" @click="resetFilters">{{ t('daily.reset') }}</button>
      </div>
    </div>
  </div>

  <QuickAdd style="margin-top:16px" />

  <div v-if="error" class="err">{{ error }}</div>
  <div v-else-if="loading" class="empty">{{ t('common.loading') }}</div>
  <div v-else style="margin-top:16px">
    <TxnList :txns="items" />
  </div>
</template>

<style scoped>
.filters-strip {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 0 0 var(--radius) var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  margin: 0 0 16px;
}
.filter-toggle.active {
  background: var(--accent);
  color: #fff;
  box-shadow: none;
}
.filter-toggle.active span { color: #fff; }
</style>