import { computed } from 'vue'
import { i18n } from './i18n'

function lc() {
  return i18n.global.locale.value === 'zh-CN' ? 'zh-CN' : 'en-CH'
}

const chfCache: Record<string, Intl.NumberFormat> = {}
const pctCache: Record<string, Intl.NumberFormat> = {}

function chfFmt(locale: string): Intl.NumberFormat {
  return (chfCache[locale] ??= new Intl.NumberFormat(locale, { style: 'currency', currency: 'CHF' }))
}
function pctFmt(locale: string): Intl.NumberFormat {
  return (pctCache[locale] ??= new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }))
}

export function money(minor: number | null | undefined): string {
  if (minor == null) return '—'
  return chfFmt(lc()).format(minor / 100)
}

export function percent(rate: number | null | undefined): string {
  if (rate == null) return '—'
  return pctFmt(lc()).format(rate)
}

export function fmtDate(d: string, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' }): string {
  return new Intl.DateTimeFormat(lc(), opts).format(new Date(d))
}

export function fmtDateLong(d: string): string {
  return new Intl.DateTimeFormat(lc(), { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(d))
}

export const localeRef = computed(lc)
