<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { dataVersion } from '../composables/useDataVersion'
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
</script>

<template>
  <h1 style="font-size:20px;margin-bottom:16px">
    {{ t('daily.title') }}
    <span class="muted" style="font-size:13px;font-weight:400">
      {{ t('daily.lastDays', { n: days }) }}
    </span>
    <button class="btn secondary no-print" style="margin-left:auto;font-size:13px;padding:5px 12px"
            @click="showFilters = !showFilters">{{ t('daily.filters') }}</button>
  </h1>

  <QuickAdd />

  <div v-if="showFilters" class="card no-print" style="margin-top:16px;margin-bottom:16px">
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
    </div>
  </div>

  <div v-if="error" class="err">{{ error }}</div>
  <div v-else-if="loading" class="empty">{{ t('common.loading') }}</div>
  <div v-else style="margin-top:16px">
    <TxnList :txns="items" />
  </div>
</template>