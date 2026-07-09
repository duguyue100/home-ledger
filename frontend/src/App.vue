<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLang } from './i18n'
import { api } from './api'
import { bumpData } from './composables/useDataVersion'
import Logo from './components/Logo.vue'

const { t, locale } = useI18n()
const lang = ref(locale.value as 'en' | 'zh-CN')
function toggle(l: 'en' | 'zh-CN') {
  lang.value = l
  setLang(l)
}

// auto-post any recurring templates due for the current month whenever the app loads.
// dup-guarded per-month on the backend, so calling repeatedly is a no-op once posted.
onMounted(async () => {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const r = await api.materializeDue(today)
    if (r?.posted?.length) bumpData()
  } catch { /* ignore — best-effort, e.g. transient network */ }
})
</script>

<template>
  <header class="topbar">
    <Logo with-text />
    <nav>
      <RouterLink to="/daily">{{ t('nav.daily') }}</RouterLink>
      <RouterLink to="/reports">{{ t('nav.reports') }}</RouterLink>
      <RouterLink to="/settings">{{ t('nav.settings') }}</RouterLink>
    </nav>
    <div class="lang-toggle">
      <button :class="{ active: lang === 'en' }" @click="toggle('en')">EN</button>
      <span>·</span>
      <button :class="{ active: lang === 'zh-CN' }" @click="toggle('zh-CN')">中</button>
    </div>
  </header>
  <main class="app-shell">
    <RouterView />
  </main>
</template>
