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
  allCategories: () => req('/categories'),
  createCategory: (c: any) => req('/categories', { method: 'POST', body: JSON.stringify(c) }),
  patchCategory: (id: number, c: any) => req(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(c) }),
  deleteCategory: (id: number) => req(`/categories/${id}`, { method: 'DELETE' }),
  reviveCategory: (id: number) =>
    req(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify({ valid_to: null }) }),
  budgets: (categoryId: number) => req(`/budgets?category_id=${categoryId}`),
  allBudgets: () => req('/budgets'),
  createBudget: (b: any) => req('/budgets', { method: 'POST', body: JSON.stringify(b) }),
  deleteBudget: (id: number) => req(`/budgets/${id}`, { method: 'DELETE' }),
  recurring: () => req('/recurring?active_only=true'),
  allRecurring: () => req('/recurring'),
  createRecurring: (r: any) => req('/recurring', { method: 'POST', body: JSON.stringify(r) }),
  deleteRecurring: (id: number) => req(`/recurring/${id}`, { method: 'DELETE' }),
  patchRecurring: (id: number, r: any) => req(`/recurring/${id}`, { method: 'PATCH', body: JSON.stringify(r) }),
  reviveRecurring: (id: number) =>
    req(`/recurring/${id}`, { method: 'PATCH', body: JSON.stringify({ valid_to: null }) }),
  materialize: (id: number, on: string, amountOverride?: number) =>
    req(`/recurring/${id}/materialize?on=${on}` + (amountOverride ? `&amount_override=${amountOverride}` : ''), { method: 'POST' }),
  materializeDue: (on: string) => req(`/recurring/materialize-due?on=${on}`, { method: 'POST' }),
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

export type Budget = {
  id: number
  category_id: number
  amount: number
  valid_from: string
  valid_to: string | null
}

export type Recurring = {
  id: number
  kind: string
  category_id: number | null
  amount: number
  currency: string
  day_of_month: number
  valid_from: string
  valid_to: string | null
  note_en: string | null
  note_zh: string | null
}
