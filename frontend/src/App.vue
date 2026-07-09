<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLang } from './i18n'
import Logo from './components/Logo.vue'

const { t, locale } = useI18n()
const lang = ref(locale.value as 'en' | 'zh-CN')
function toggle(l: 'en' | 'zh-CN') {
  lang.value = l
  setLang(l)
}
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
