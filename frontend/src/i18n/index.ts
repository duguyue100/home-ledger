import { createI18n } from 'vue-i18n'
import en from './en.json'
import zh from './zh-CN.json'

const stored = (localStorage.getItem('hl-lang') as 'en' | 'zh-CN') || 'en'

export const i18n = createI18n({
  legacy: false,
  locale: stored,
  fallbackLocale: 'en',
  messages: { en, 'zh-CN': zh },
})

export function setLang(l: 'en' | 'zh-CN') {
  i18n.global.locale.value = l
  localStorage.setItem('hl-lang', l)
}

export function localeForIntl(): string {
  return i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'
}
