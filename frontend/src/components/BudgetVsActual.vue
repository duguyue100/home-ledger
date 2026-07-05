<script setup lang="ts">
import { money, percent } from '../format'
import { useI18n } from 'vue-i18n'

defineProps<{ rows: any[]; locale: string }>()
const { t } = useI18n()
</script>

<template>
  <div v-if="!rows.length" class="empty">—</div>
  <div v-for="r in rows" :key="r.category_id" class="budget-row">
    <div class="name">{{ locale === 'zh-CN' && r.name_zh ? r.name_zh : r.name_en }}</div>
    <div class="bar">
      <span :class="{ over: r.overspent }" :style="{ width: Math.min(100, (r.budget ? (r.spent / r.budget) * 100 : 100)) + '%' }"></span>
    </div>
    <div class="nums">
      {{ money(r.spent) }} / {{ money(r.budget) }}
      <span v-if="r.overspent" style="color:var(--red)"> · ⚠ {{ t('budget.overspent') }}</span>
      <span v-else-if="r.borrowed_carried > 0" style="color:var(--amber)"> · −{{ money(r.borrowed_carried) }} {{ t('budget.carry') }}</span>
    </div>
  </div>
</template>