"""Calculation layer: pure functions over a Session.

All money is integer CHF minor units. Borrowing entries are budget markers, never
counted as spending (the overspend itself is already a `spending` transaction).
"""
import statistics
from datetime import date, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Budget, Category, Recurring, Transaction

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


# ---- enrichment stats ----


def _pct(cur: int | float, prev: int | float) -> float | None:
    """Percentage change (cur-prev)/prev. None when prev is 0 (avoids div-by-zero)."""
    if not prev:
        return None
    return (cur - prev) / prev


def deltas(session: Session, year: int, month: int) -> dict:
    """MoM and YoY pct change for income/spending/net.

    Returns has_mom/has_yoy flags so the UI can hide missing comparisons.
    """
    cur_s, cur_e = month_bounds(year, month)
    cur = summary(session, cur_s, cur_e)

    py, pm = previous_month(year, month)
    prev_s, prev_e = month_bounds(py, pm)
    prev = summary(session, prev_s, prev_e)
    has_mom = bool(prev["income"] or prev["spending"] or prev["investment"])

    yoy_year = year - 1
    yoy_s, yoy_e = month_bounds(yoy_year, month)
    yoy = summary(session, yoy_s, yoy_e)
    has_yoy = bool(yoy["income"] or yoy["spending"] or yoy["investment"])

    return {
        "mom": {
            "income": _pct(cur["income"], prev["income"]),
            "spending": _pct(cur["spending"], prev["spending"]),
            "net": _pct(cur["net"], prev["net"]),
        },
        "yoy": {
            "income": _pct(cur["income"], yoy["income"]),
            "spending": _pct(cur["spending"], yoy["spending"]),
            "net": _pct(cur["net"], yoy["net"]),
        },
        "has_mom": has_mom,
        "has_yoy": has_yoy,
    }


def recurring_annualized(session: Session, on: date | None = None) -> dict:
    """Annualized cost of active recurring templates (spending+borrowing only).

    Excludes income (salary) and investment kinds — those aren't subscriptions.
    """
    on = on or date.today()
    rows = session.exec(
        select(Recurring)
        .where(Recurring.kind.in_(("spending", "borrowing")))
        .where(Recurring.valid_from <= on)
        .where((Recurring.valid_to == None) | (Recurring.valid_to > on))  # noqa: E711
        .order_by(Recurring.amount.desc())
    ).all()
    items = []
    total = 0
    for r in rows:
        monthly = r.amount
        annual = monthly * 12
        total += annual
        items.append({
            "id": r.id,
            "note": r.note_en or r.note_zh or "(no note)",
            "monthly": monthly,
            "annual": annual,
            "kind": r.kind,
        })
    return {"total_annual": total, "count": len(items), "items": items}


def tag_breakdown(session: Session, start: date, end: date) -> list[dict]:
    """Spending grouped by tag, descending by total. Only non-null tags."""
    rows = session.execute(
        select(
            Transaction.tag,
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .where(Transaction.kind.in_(KINDS_SPENDING))
        .where(Transaction.occurred_on >= start)
        .where(Transaction.occurred_on < end)
        .where(Transaction.tag != None)  # noqa: E711
        .where(Transaction.tag != "")
        .group_by(Transaction.tag)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    return [{"tag": r[0], "total": int(r[1]), "count": int(r[2])} for r in rows]


def savings_rate_stats(
    session: Session, year: int, month: int, target: float = 0.30, months: int = 12
) -> dict:
    """Trailing-N savings-rate benchmarks: current/median/best/worst + months above target."""
    rates: list[float] = []
    y, m = year, month
    current: float | None = None
    for i in range(months):
        r = savings_rate(session, y, m)
        if r is not None:
            rates.append(r)
            if i == 0:
                current = r
        y, m = previous_month(y, m)
    if not rates:
        return {
            "current": None, "median": None, "best": None, "worst": None,
            "months_above_target": 0, "months_with_data": 0, "target": target,
        }
    return {
        "current": current,
        "median": statistics.median(rates),
        "best": max(rates),
        "worst": min(rates),
        "months_above_target": sum(1 for r in rates if r >= target),
        "months_with_data": len(rates),
        "target": target,
    }


def spending_volatility(
    session: Session, year: int, month: int, months: int = 12
) -> dict:
    """Trailing-N monthly spending stats: mean/std/cv/min/max.

    CV (coefficient of variation) = std/mean. Lower = more predictable life.
    Uses population std (pstdev) since the window IS the full population of interest.
    """
    totals: list[int] = []
    y, m = year, month
    for _ in range(months):
        s, e = month_bounds(y, m)
        totals.append(_sum_amounts(session, KINDS_SPENDING, s, e))
        y, m = previous_month(y, m)
    # drop trailing zero months (no data yet) from the END only — keep leading zeros
    # (real zero-spend months within tracked history)
    while totals and totals[-1] == 0:
        totals.pop()
    if not totals:
        return {"mean": 0, "std": 0, "cv": 0, "min": 0, "max": 0, "months": 0}
    mean = statistics.mean(totals)
    std = statistics.pstdev(totals)
    cv = std / mean if mean else 0
    return {
        "mean": int(mean),
        "std": int(std),
        "cv": cv,
        "min": min(totals),
        "max": max(totals),
        "months": len(totals),
    }


def fixed_vs_discretionary(session: Session, start: date, end: date) -> dict:
    """Split spending into fixed (committed) vs discretionary, by Category.is_fixed."""
    rows = session.execute(
        select(
            Category.is_fixed,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.kind.in_(KINDS_SPENDING))
        .where(Transaction.occurred_on >= start)
        .where(Transaction.occurred_on < end)
        .group_by(Category.is_fixed)
    ).all()
    fixed = 0
    disc = 0
    for is_fixed, total in rows:
        if is_fixed:
            fixed += int(total)
        else:
            disc += int(total)
    total = fixed + disc
    return {
        "fixed": fixed,
        "discretionary": disc,
        "total": total,
        "fixed_pct": fixed / total if total else 0,
        "disc_pct": disc / total if total else 0,
    }


def ytd_projection(session: Session, year: int) -> dict:
    """Year-to-date annualized projection + per-category status vs yearly budget.

    months_elapsed = months from start of year through today's month (caps at
    12 for past years, so projected_annual == actual spend for complete years).
    A month with zero spend still counts as elapsed — life can have quiet months.
    """
    ys, ye = year_bounds(year)
    spent_ytd = _sum_amounts(session, KINDS_SPENDING, ys, ye)
    today = date.today()
    if today.year > year:
        months_elapsed = 12  # past year, fully elapsed
    elif today.year == year:
        months_elapsed = max(1, today.month)  # current year, through this month
    else:
        months_elapsed = 0  # future year, no data
    is_complete = months_elapsed == 12
    projected_annual = spent_ytd * 12 // months_elapsed if months_elapsed else spent_ytd

    cats = session.exec(
        select(Category)
        .where(Category.budget_period != "none")
        .where((Category.valid_to == None) | (Category.valid_to > ys))  # noqa: E711
        .where(Category.valid_from < ye)
        .order_by(Category.name_en)
    ).all()
    by_category = []
    for c in cats:
        kinds = (KINDS_SPENDING + KINDS_INVESTMENT) if c.budget_period == "yearly" else KINDS_SPENDING
        spent = _sum_amounts(session, kinds, ys, ye, c.id)
        projected = spent * 12 // months_elapsed if months_elapsed else spent
        # yearly budget total (mirror budget_vs_actual_year logic)
        budget_total = 0
        last_b = 0
        months_active = 0
        for m in range(1, 13):
            on_m = date(year, m, 1)
            if c.valid_from > on_m:
                continue
            b = budget_as_of(session, c.id, on_m)
            if b is None:
                continue
            months_active += 1
            last_b = b
            if c.budget_period != "yearly":
                budget_total += b
        if c.budget_period == "yearly" and months_active:
            budget_total = last_b * months_active // 12
        if not budget_total:
            continue
        ratio = projected / budget_total if budget_total else 0
        status = "over" if ratio > 1.1 else "at-risk" if ratio > 1.0 else "on-track"
        by_category.append({
            "name_en": c.name_en,
            "name_zh": c.name_zh or c.name_en,
            "spent": spent,
            "projected": projected,
            "budget": budget_total,
            "status": status,
        })
    return {
        "spent_ytd": spent_ytd,
        "months_elapsed": months_elapsed,
        "projected_annual": projected_annual,
        "is_complete": is_complete,
        "by_category": by_category,
    }
