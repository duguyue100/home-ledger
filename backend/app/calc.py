"""Calculation layer: pure functions over a Session.

All money is integer CHF minor units. Borrowing entries are budget markers, never
counted as spending (the overspend itself is already a `spending` transaction).
"""
from datetime import date, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Budget, Category, Transaction

KINDS_INCOME = ("income",)
KINDS_SPENDING = ("spending",)
KINDS_INVESTMENT = ("investment",)
KINDS_BORROWING = ("borrowing",)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """(first_day, first_day_of_next_month). End is exclusive."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def day_bounds(on: date) -> tuple[date, date]:
    return on, on + timedelta(days=1)


def year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1)


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def convert_to_chf(original_minor: int, rate: float) -> int:
    """Foreign minor units -> CHF minor units.

    `rate` = CHF (major) per 1 unit of foreign currency (major).
    Assumes both currencies use 100 minor per major (CHF + CNY both do).
    ponytail: JPY (0 minor) needs a per-currency scale; add when used.
    """
    return round(original_minor * rate)


def budget_as_of(session: Session, category_id: int, on: date) -> int | None:
    row = session.exec(
        select(Budget)
        .where(Budget.category_id == category_id)
        .where(Budget.valid_from <= on)
        .where((Budget.valid_to == None) | (Budget.valid_to > on))  # noqa: E711
        .order_by(Budget.valid_from.desc())
    ).first()
    return row.amount if row else None


def _sum_amounts(
    session: Session,
    kinds: tuple[str, ...],
    start: date,
    end: date,
    category_id: int | None = None,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.kind.in_(kinds))
        .where(Transaction.occurred_on >= start)
        .where(Transaction.occurred_on < end)
    )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    return int(session.execute(stmt).scalar() or 0)


def spent_in_month(session: Session, category_id: int, year: int, month: int) -> int:
    s, e = month_bounds(year, month)
    return _sum_amounts(session, KINDS_SPENDING, s, e, category_id)


def borrowed_in_month(
    session: Session, category_id: int, year: int, month: int
) -> int:
    s, e = month_bounds(year, month)
    return _sum_amounts(session, KINDS_BORROWING, s, e, category_id)


def income_in_month(session: Session, year: int, month: int) -> int:
    s, e = month_bounds(year, month)
    return _sum_amounts(session, KINDS_INCOME, s, e)


def investment_in_month(session: Session, year: int, month: int) -> int:
    s, e = month_bounds(year, month)
    return _sum_amounts(session, KINDS_INVESTMENT, s, e)


def available_for_month(
    session: Session, category_id: int, year: int, month: int
) -> int | None:
    """Budget for the month minus borrowing carried over from the previous month."""
    budget = budget_as_of(session, category_id, date(year, month, 1))
    if budget is None:
        return None
    py, pm = previous_month(year, month)
    carried = borrowed_in_month(session, category_id, py, pm)
    return budget - carried


def overspent(
    session: Session, category_id: int, year: int, month: int
) -> bool | None:
    avail = available_for_month(session, category_id, year, month)
    if avail is None:
        return None
    return spent_in_month(session, category_id, year, month) > avail


def budget_vs_actual(
    session: Session, year: int, month: int
) -> list[dict]:
    rows = session.exec(
        select(Category)
        .where(Category.budget_period == "monthly")
        .where((Category.valid_to == None) | (Category.valid_to > date(year, month, 1)))  # noqa: E711
        .order_by(Category.name_en)
    ).all()
    out = []
    for c in rows:
        avail = available_for_month(session, c.id, year, month)
        spent = spent_in_month(session, c.id, year, month)
        py, pm = previous_month(year, month)
        carried = borrowed_in_month(session, c.id, py, pm)
        budget = budget_as_of(session, c.id, date(year, month, 1)) or 0
        out.append({
            "category_id": c.id,
            "name_en": c.name_en,
            "name_zh": c.name_zh or c.name_en,
            "budget": budget,
            "spent": spent,
            "borrowed_carried": carried,
            "available": avail if avail is not None else budget,
            "overspent": bool(avail is not None and spent > avail),
        })
    return out


def savings_rate(session: Session, year: int, month: int) -> float | None:
    """(income - spending) / income. Borrowing & investment excluded."""
    income = income_in_month(session, year, month)
    if income == 0:
        return None
    s, e = month_bounds(year, month)
    spending = _sum_amounts(session, KINDS_SPENDING, s, e)
    return (income - spending) / income


def savings_rate_rolling(
    session: Session, year: int, month: int, months: int = 3
) -> float | None:
    income = 0
    spending = 0
    y, m = year, month
    for _ in range(months):
        s, e = month_bounds(y, m)
        income += _sum_amounts(session, KINDS_INCOME, s, e)
        spending += _sum_amounts(session, KINDS_SPENDING, s, e)
        y, m = previous_month(y, m)
    if income == 0:
        return None
    return (income - spending) / income


def savings_rate_year(session: Session, year: int) -> float | None:
    """Annual savings rate = (income - spending) / income for the calendar year.

    Borrowing and investment excluded, same as monthly savings_rate.
    """
    s, e = year_bounds(year)
    income = _sum_amounts(session, KINDS_INCOME, s, e)
    if income == 0:
        return None
    spending = _sum_amounts(session, KINDS_SPENDING, s, e)
    return (income - spending) / income


def budget_vs_actual_year(session: Session, year: int) -> list[dict]:
    """Yearly budget-vs-actual. YTD totals per category, same row shape as monthly.

    - monthly-period category: budget = monthly_amount * months_active_in_year
    - yearly-period category:   budget = yearly_amount * (months_active_in_year / 12)
    - spent = sum of spending txns in [year-01-01, year+1-01-01)
    - borrowed_carried, overspent left as 0/False (carryover is a monthly concept)
    """
    ys, ye = year_bounds(year)
    rows = session.exec(
        select(Category)
        .where((Category.valid_to == None) | (Category.valid_to > ys))  # noqa: E711
        .where(Category.valid_from < ye)
        .where(Category.budget_period != "none")
        .order_by(Category.name_en)
    ).all()
    out = []
    for c in rows:
        # yearly-period categories (e.g. Investment) count investment outflows as spend.
        kinds = (KINDS_SPENDING + KINDS_INVESTMENT) if c.budget_period == "yearly" else KINDS_SPENDING
        spent = _sum_amounts(session, kinds, ys, ye, c.id)
        # sum monthly budgets as-of each month of the year
        budget_total = 0
        months_active = 0
        last_b = 0
        for m in range(1, 13):
            on = date(year, m, 1)
            if c.valid_from > on:
                continue
            b = budget_as_of(session, c.id, on)
            if b is None:
                continue
            months_active += 1
            last_b = b
            if c.budget_period != "yearly":
                budget_total += b
        if c.budget_period == "yearly" and months_active:
            # prorated yearly total (floor div once to avoid centime drift)
            budget_total = last_b * months_active // 12
        out.append({
            "category_id": c.id,
            "name_en": c.name_en,
            "name_zh": c.name_zh or c.name_en,
            "budget": budget_total,
            "spent": spent,
            "borrowed_carried": 0,
            "available": budget_total,
            "overspent": spent > budget_total if budget_total else False,
        })
    return out


def monthly_summaries(session: Session, year: int) -> list[dict]:
    """Per-month summary for a year (income/spending/investment/net/y/m)."""
    out = []
    for m in range(1, 13):
        s, e = month_bounds(year, m)
        sm = summary(session, s, e)
        out.append({"y": year, "m": m, **sm})
    return out


def category_breakdown(
    session: Session, start: date, end: date
) -> list[dict]:
    rows = session.execute(
        select(
            Category.id,
            Category.name_en,
            Category.name_zh,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.kind.in_(KINDS_SPENDING))
        .where(Transaction.occurred_on >= start)
        .where(Transaction.occurred_on < end)
        .group_by(Category.id, Category.name_en, Category.name_zh)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    return [
        {
            "category_id": r[0],
            "name_en": r[1],
            "name_zh": r[2] or r[1],
            "total": int(r[3]),
        }
        for r in rows
    ]


def summary(session: Session, start: date, end: date) -> dict:
    income = _sum_amounts(session, KINDS_INCOME, start, end)
    spending = _sum_amounts(session, KINDS_SPENDING, start, end)
    investment = _sum_amounts(session, KINDS_INVESTMENT, start, end)
    return {
        "income": income,
        "spending": spending,
        "investment": investment,
        "net": income - spending - investment,
    }
