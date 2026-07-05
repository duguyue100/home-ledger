"""Seed the DB with fake-but-realistic data for dev.

Run inside the container:
    docker compose exec app python -m app.seed          # upsert by external_id
    docker compose exec app python -m app.seed --clear  # wipe all rows first

Money is CHF minor units (1 CHF = 100). All seed rows carry external_id="seed:..."
so re-running is safe (upserts, no duplicates) without --clear.
"""
from datetime import date
from datetime import timedelta as _td

from sqlmodel import Session, delete, select

from app.db import engine, init_db
from app.models import Budget, Category, Recurring, Transaction
from app.routes import TxnBulkItem, bulk_upsert_transactions

# reference "today" anchored to a fixed date so the dataset is deterministic
TODAY = date(2026, 7, 5)

DEFAULT_CATEGORIES = [
    # (name_en, name_zh, budget_period, monthly_amount)
    ("Groceries & Food", "食品杂货", "monthly", 80000),   # 800
    ("Housing", "住房", "monthly", 180000),               # 1800 (rent-like)
    ("Transportation", "交通", "monthly", 20000),          # 200
    ("Insurance", "保险", "monthly", 30000),               # 300
    ("Communication", "通讯", "monthly", 8000),            # 80
    ("Personal", "个人", "monthly", 40000),                # 400
    ("Tax", "税务", "yearly", 50000),                      # 500/year
    ("Investment", "投资", "yearly", 600000),              # 6000/year
]


def _clear(session: Session) -> None:
    for t in (Transaction, Budget, Recurring, Category):
        session.exec(delete(t))
    session.commit()


def _seed_categories(session: Session) -> dict[str, int]:
    ids = {}
    for name_en, name_zh, period, _ in DEFAULT_CATEGORIES:
        existing = session.exec(
            select(Category).where(Category.name_en == name_en)
        ).first()
        if existing:
            existing.name_zh = name_zh
            existing.budget_period = period
            existing.valid_to = None
            session.add(existing)
            c = existing
        else:
            c = Category(
                name_en=name_en, name_zh=name_zh,
                budget_period=period, valid_from=date(2026, 1, 1),
            )
            session.add(c)
        session.commit()
        session.refresh(c)
        ids[name_en] = c.id
    return ids


def _seed_budgets(session: Session, ids: dict[str, int]) -> None:
    for name_en, _zh, period, amount in DEFAULT_CATEGORIES:
        cid = ids[name_en]
        existing = session.exec(
            select(Budget).where(Budget.category_id == cid)
            .where((Budget.valid_to == None))  # noqa: E711
        ).first()
        if existing:
            existing.amount = amount
            existing.valid_from = date(2026, 1, 1)
            session.add(existing)
        else:
            session.add(Budget(
                category_id=cid, amount=amount, valid_from=date(2026, 1, 1),
            ))
    session.commit()


def _seed_recurring(session: Session, ids: dict[str, int]) -> dict[str, int]:
    specs = [
        ("salary", "income", None, 600000, 25, "Salary", "工资"),
        ("rent", "spending", "Housing", 180000, 1, "Rent", "房租"),
        ("travelcard", "spending", "Transportation", 12000, 5, "Monthly travel card", "月票"),
        ("phone", "spending", "Communication", 5500, 10, "Phone bill", "话费"),
    ]
    rids = {}
    for key, kind, cat_name, amount, dom, note_en, note_zh in specs:
        existing = session.exec(
            select(Recurring).where(Recurring.note_en == note_en)
        ).first()
        if existing:
            existing.kind = kind
            existing.category_id = ids.get(cat_name) if cat_name else None
            existing.amount = amount
            existing.day_of_month = dom
            existing.valid_from = date(2026, 1, 1)
            existing.valid_to = None
            existing.note_zh = note_zh
            session.add(existing)
            r = existing
        else:
            r = Recurring(
                kind=kind, category_id=ids.get(cat_name) if cat_name else None,
                amount=amount, day_of_month=dom, valid_from=date(2026, 1, 1),
                note_en=note_en, note_zh=note_zh,
            )
            session.add(r)
        session.commit()
        session.refresh(r)
        rids[key] = r.id
    return rids


def _seed_transactions(session: Session, ids: dict[str, int]) -> None:
    months = [date((TODAY - _td(days=30 * b)).year, (TODAY - _td(days=30 * b)).month, 1)
              for b in (2, 1, 0)]

    # (occurred_on, kind, amount, category_name|None, note, tag, original_amount, original_currency)
    specs: list[tuple] = []
    for m in months:
        specs.append((date(m.year, m.month, 25), "income", 600000, None, "Salary", None, None, None))
        specs.append((date(m.year, m.month, 1), "spending", 180000, "Housing", "Rent", None, None, None))
        specs.append((date(m.year, m.month, 5), "spending", 12000, "Transportation", "Travel card", None, None, None))
        specs.append((date(m.year, m.month, 10), "spending", 5500, "Communication", "Phone", None, None, None))
        for day, amt in ((3, 4500), (8, 6200), (15, 5100), (22, 4800), (27, 3900)):
            specs.append((date(m.year, m.month, day), "spending", amt, "Groceries & Food", "Groceries", None, None, None))
        specs.append((date(m.year, m.month, 12), "spending", 15000, "Personal", "Misc", None, None, None))
        if m.month in (5, 7):
            specs.append((date(m.year, m.month, 18), "spending", 30000, "Insurance", "Insurance", None, None, None))
        specs.append((date(m.year, m.month, 20), "investment", 50000, None, "ETF purchase", None, None, None))

    # edge cases: CNY spend, extra income, borrowing, overspend ticket
    specs += [
        (date(2026, 6, 14), "spending", 4000, "Transportation", "China trip taxi", "trip:china-2026", 32000, "CNY"),
        (date(2026, 5, 9), "income", 75000, None, "Tax refund", None, None, None),
        (date(2026, 6, 28), "borrowing", 3000, "Transportation", "Borrow from July budget", None, None, None),
        (date(2026, 7, 3), "spending", 9500, "Transportation", "Extra train ticket", None, None, None),
    ]

    items = [
        TxnBulkItem(
            occurred_on=on, kind=kind, amount=amt, category_name=cat, note=note, tag=tag,
            original_amount=oamt, original_currency=ocur, external_id=f"seed:{i}",
        )
        for i, (on, kind, amt, cat, note, tag, oamt, ocur) in enumerate(specs)
    ]
    bulk_upsert_transactions(session, items)


def main(clear: bool = False) -> None:
    from app.db import DB_PATH

    init_db()
    with Session(engine) as session:
        if clear:
            _clear(session)
        ids = _seed_categories(session)
        _seed_budgets(session, ids)
        _seed_recurring(session, ids)
        _seed_transactions(session, ids)
    print(f"seeded {'(after clear) ' if clear else ''}into {DB_PATH}")


if __name__ == "__main__":
    import sys
    main(clear="--clear" in sys.argv)
