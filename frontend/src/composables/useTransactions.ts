import { ref, watch } from 'vue'
import { api, type Txn } from '../api'
import { dataVersion } from './useDataVersion'

export function useTransactions(params: () => Record<string, any>) {
  const items = ref<Txn[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      items.value = await api.transactions(params())
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  watch(dataVersion, load)
  watch(() => JSON.stringify(params()), load, { immediate: true })
  return { items, loading, error, reload: load }
}
