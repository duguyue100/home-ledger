import { ref, watch } from 'vue'
import { api, type Category } from '../api'
import { dataVersion } from './useDataVersion'

const cats = ref<Category[]>([])
const catsAll = ref<Category[]>([])
const loaded = ref(false)

async function load() {
  cats.value = await api.categories()
  catsAll.value = await api.allCategories()
  loaded.value = true
}

watch(dataVersion, load)
if (!loaded.value) load()

export function useCategories() {
  return { categories: cats, allCategories: catsAll, reload: load }
}

// bilingual name based on current locale
export function categoryName(c: Category | undefined | null, locale: string): string {
  if (!c) return '—'
  return locale === 'zh-CN' && c.name_zh ? c.name_zh : c.name_en
}

export function findCategory(id: number | null): Category | undefined {
  return cats.value.find((c) => c.id === id)
}
