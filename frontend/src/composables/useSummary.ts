import { ref, watch } from 'vue'
import { api } from '../api'
import { dataVersion } from './useDataVersion'

export function useSummary(period: () => string, d: () => string) {
  const data = ref<any>(null)
  const loading = ref(false)
  async function load() {
    loading.value = true
    try {
      data.value = await api.summary(period(), d())
    } finally {
      loading.value = false
    }
  }
  watch(dataVersion, load)
  watch(() => period() + '|' + d(), load, { immediate: true })
  return { data, loading, reload: load }
}