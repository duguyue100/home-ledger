# home-ledger

Personal home budgeting & expense tracking webapp. Runs locally in one
container, stores everything in a single SQLite file you can drop in a private
repo. Bilingual (EN primary, 中文), card-based UI, evidence-based charts.

Built for one local user who wants data, not a spreadsheet.

## Quick start

```bash
docker compose up --build -d
docker compose exec app python -m app.seed --clear   # fake data for poking around
```

Open http://localhost:5120.

Seed populates 3 months of realistic CHF transactions, one CNY spend (with
manual FX), a tax refund, a borrowing entry carrying into the next month, and a
yearly `Tax` + `Investment` category. Idempotent — re-run without `--clear` is
safe (upserts by `external_id="seed:..."`).

## What it does

- **Daily view** — card timeline of the last *N* days (default 10), with a
  quick-add form pinned at top. Filter drawer: kind, category, tag, note
  substring, window.
- **Dashboard** — three tiles (today / this month / this year), spending breakdown
  by category, 6-month savings-rate line, budget-vs-actual with overspend flags
  and borrow carryover. All charts refetch on every add / delete.
- **Report** — monthly printable view: summary tiles, breakdown by category with
  share %, budget vs actual, top 5 transactions. Yearly is a date-range on the
  same endpoint (UI deferred).
- **Settings** — add / expire categories (with initial budget), add recurring
  templates, one-click "post this month" materialization.
- **Bulk import** — JSON upsert API keyed by `external_id`, category resolved by
  name. Drive it from a spreadsheet parser script over localhost. See
  `POST /api/transactions/bulk` below.
- **i18n** — EN / 中 toggle in the top right, persisted in `localStorage`.
  Category names come from the DB's bilingual columns; dates / numbers / currency
  via `Intl`. EN is the primary view.

## Develop

Backend tests and lint run on the host via `uv`; the running app runs in Docker.

```bash
# one-time
cd backend
uv venv --python 3.12
unset VIRTUAL_ENV   # if a different venv is active in your shell
uv pip install -e ".[dev]" --python .venv/bin/python

# tests + lint
uv run pytest -q
uv run ruff check app
```

Frontend with Vite HMR (proxies `/api` → the running container on :5120):

```bash
docker compose up -d                 # backend keeps running
cd frontend && npm install && npm run dev
# open http://localhost:5173
```

Rebuild the production image after frontend changes:

```bash
docker compose up --build -d
```

## Data model

5 tables, all money in **integer minor units** (CHF centimes — 1 CHF = 100).
`valid_from` / `valid_to` implement expire-and-replace for history; `valid_to`
is exclusive, `NULL` = still active.

- `categories` — `name_en`, `name_zh`, `budget_period` (monthly | yearly | none),
  `valid_from`, `valid_to`.
- `budgets` — `category_id`, `amount`, `valid_from`, `valid_to`. One active row
  per category at a time; create-new expires any overlapping row automatically.
- `recurring` — `kind` (income | spending | investment), `category_id`,
  `amount`, `currency`, `day_of_month` (1–28), `valid_from`, `valid_to`,
  `note_en`, `note_zh`. Templates only — never events. Materialize-on-click.
- `transactions` — the ledger. `kind` adds `borrowing` to the recurring list.
  `category_id` nullable (income has no category). `original_amount` /
  `original_currency` set when spent in foreign currency; `amount` is the CHF
  conversion stored at entry time (no FX table, no live rate fetch). `tag`
  free-text (e.g. `trip:china-2026`). `source_recurring_id` points back to the
  template if materialized. `external_id` is the bulk-upsert key.

### Design rules (pinned by tests)

- **Income change** → expire the recurring template at the old amount, create a
  new one with `valid_from` = change month. Never edit history.
- **Borrowing** is a budget marker, not new money. It reduces the *next* month's
  available for that category and is **excluded** from savings-rate spending
  (the overspend is already a `spending` entry; double-count avoided).
- **FX** is captured per transaction at entry time. Historical spends stay
  correct forever; no rate table to rot.
- **Tax** → a category with `budget_period=yearly`.
- **Trip / irregular spend** → plain `spending` with a `tag`. Filterable.
- **Extra train ticket in a fixed-budget category** → plain `spending`. The
  overspend shows red — that's the signal. No special handling.

## API surface

All under `/api`, no auth (localhost single-user). Money in minor units.
Dates ISO `YYYY-MM-DD`. Filters use `from` / `to` (end exclusive).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness |
| `GET`/`POST`/`PATCH` | `/categories` | list (active-only filter) / create / expire |
| `POST` | `/categories/bulk` | upsert by `name_en` |
| `GET`/`POST` | `/budgets` | list (with `as_of` history lookup) / create (auto-expires overlaps) |
| `POST` | `/budgets/bulk` | upsert |
| `GET`/`POST` | `/recurring` | list (active-only) / create |
| `POST` | `/recurring/{id}/materialize?on=&amount_override=` | post one month's instance (dup-guarded) |
| `POST` | `/recurring/bulk` | insert |
| `GET`/`POST`/`GET /{id}`/`PATCH /{id}`/`DELETE /{id}` | `/transactions` | CRUD with filters: `from`, `to`, `kind` (multi), `category_id`, `tag`, `currency`, `recurring` (bool), `q` (note substring), `limit`, `offset` |
| `POST` | `/transactions/bulk` | upsert by `external_id`; `category_name` resolved (created if missing) |
| `GET` | `/summary?period=day\|month\|year&d=` | income / spending / investment / net |
| `GET` | `/breakdown?from=&to=` | spending grouped by category, desc |
| `GET` | `/budget-vs-actual?year=&month=` | per active category: budget, spent, borrowed_carried, available, overspent |
| `GET` | `/savings-rate?year=&month=&roll=0` | `(income − spending) / income`; `roll` for N-month rolling |
| `GET` | `/report?month=` | full payload for the printable view |

### Bulk import example

```bash
curl -s localhost:8000/api/transactions/bulk -H 'Content-Type: application/json' -d '[
  {"occurred_on":"2026-07-01","kind":"spending","amount":1545,
   "category_name":"Groceries & Food","note":"Migros","external_id":"sheet:r42"},
  {"occurred_on":"2026-06-14","kind":"spending","amount":4000,
   "original_amount":32000,"original_currency":"CNY",
   "category_name":"Transportation","note":"China taxi","external_id":"sheet:r43"}
]'
# -> {"created":2,"updated":0}
```

Re-run with the same `external_id`s to update (e.g. after fixing a parser bug) —
no duplicates. Without `external_id`, every row is a fresh insert.

## Persistence

`./data/ledger.db` is bind-mounted into the container. The host file is the
source of truth. To back up, from the host:

```bash
git -C /path/to/private-repo add ledger.db   # copy or symlink it there
git -C /path/to/private-repo commit -m "ledger $(date +%F)"
```

Manual, no automation. Volume location: `data/` in the repo root
(gitignored in this repo). A `/snapshot` endpoint (`VACUUM INTO …`) is deferred
— say the word if you want it.

## Tech

| Layer | Pick |
|---|---|
| Backend | FastAPI · SQLModel · Python 3.12 |
| DB | SQLite, single file, bind-mounted |
| Frontend | Vite · Vue 3 · TypeScript · vue-router · vue-i18n · Chart.js |
| UI | hand-written CSS (no component lib) |
| State | composables + a global `dataVersion` ref (refetch-on-mutation = live charts) |
| Containers | one service (API + built static + SPA fallback) |
| Deps | `uv` (backend) · `npm` (frontend) |

## Layout

```
backend/
  app/{main,db,models,calc,routes,seed}.py
  app/tests/{conftest,test_schema,test_calc,test_bulk}.py   # 19 tests, non-trivial only
frontend/
  src/{main,router,api,format}.ts
  src/i18n/{en,zh-CN}.json
  src/composables/   useDataVersion · useCategories · useTransactions · useSummary
  src/components/    QuickAdd · TxnCard · TxnList · CategoryBar · SavingsRateLine · BudgetVsActual
  src/views/         Daily · Dashboard · Report · Settings
  src/style/base.css
data/                gitignored; holds ledger.db
Dockerfile           multi-stage: build frontend → uv install backend → serve both
docker-compose.yml   one service, volume: ./data:/app/data
PLAN.md              full technical plan and design resolutions
```

## Deferred (YAGNI — add when asked)

accounts / per-account net worth · multi-user / auth · auto-cron recurring · FX
rate auto-fetch · `/snapshot` endpoint · automated backup cron · yearly report
UI (endpoint already supports it) · net-worth-flow chart · YoY comparison ·
FX-adjusted trends · Pinia (composables are fine) · SSE / WebSocket.

See `PLAN.md` for the full rationale and the resolved open questions.

## License

See `LICENSE`.