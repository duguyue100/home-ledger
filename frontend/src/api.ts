const BASE = '/api'

async function req(path: string, opts?: RequestInit): Promise<any> {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

function qs(params: Record<string, any>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => q.append(k, String(x)))
    else q.set(k, String(v))
  }
  const s = q.toString()
  return s ? '?' + s : ''
}

export const api = {
  health: () => req('/health'),
  transactions: (params: Record<string, any> = {}) => req('/transactions' + qs(params)),
  createTxn: (t: any) => req('/transactions', { method: 'POST', body: JSON.stringify(t) }),
  patchTxn: (id: number, t: any) => req(`/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(t) }),
  deleteTxn: (id: number) => req(`/transactions/${id}`, { method: 'DELETE' }),
  categories: () => req('/categories?active_only=true'),
  createCategory: (c: any) => req('/categories', { method: 'POST', body: JSON.stringify(c) }),
  patchCategory: (id: number, c: any) => req(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(c) }),
  budgets: (categoryId: number) => req(`/budgets?category_id=${categoryId}`),
  createBudget: (b: any) => req('/budgets', { method: 'POST', body: JSON.stringify(b) }),
  recurring: () => req('/recurring?active_only=true'),
  createRecurring: (r: any) => req('/recurring', { method: 'POST', body: JSON.stringify(r) }),
  materialize: (id: number, on: string, amountOverride?: number) =>
    req(`/recurring/${id}/materialize?on=${on}` + (amountOverride ? `&amount_override=${amountOverride}` : ''), { method: 'POST' }),
  summary: (period: string, d: string) => req(`/summary?period=${period}&d=${d}`),
  breakdown: (from: string, to: string) => req(`/breakdown?from=${from}&to=${to}`),
  budgetVsActual: (y: number, m: number) => req(`/budget-vs-actual?year=${y}&month=${m}`),
  savingsRate: (y: number, m: number, roll = 0) =>
    req(`/savings-rate?year=${y}&month=${m}` + (roll ? `&roll=${roll}` : '')),
  report: (ref: string, period: 'month' | 'year' = 'month') =>
    req(`/report?ref=${ref}&period=${period}`),
}

export type Txn = {
  id: number
  occurred_on: string
  kind: 'income' | 'spending' | 'investment' | 'borrowing'
  category_id: number | null
  amount: number
  currency: string
  original_amount: number | null
  original_currency: string | null
  note: string | null
  tag: string | null
  source_recurring_id: number | null
  external_id: string | null
}

export type Category = {
  id: number
  name_en: string
  name_zh: string | null
  budget_period: 'monthly' | 'yearly' | 'none'
  valid_from: string
  valid_to: string | null
}
