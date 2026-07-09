from datetime import date

from app import calc
from app.models import Budget, Category, Recurring, Transaction


def _cat(session, name="Food", period="monthly", valid_from=date(2026, 1, 1)):
    c = Category(name_en=name, budget_period=period, valid_from=valid_from)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _budget(session, cat_id, amount, frm=date(2026, 1, 1), to=None):
    session.add(Budget(category_id=cat_id, amount=amount, valid_from=frm, valid_to=to))
    session.commit()


def _txn(session, on, kind, amount, cat_id=None, **kw):
    session.add(Transaction(
        occurred_on=on, kind=kind, amount=amount, category_id=cat_id, **kw
    ))
    session.commit()


# ---- FX ----

def test_convert_to_chf_cny():
    # 100 CNY = 10000 fen; rate 0.125 CHF/CNY -> 12.50 CHF = 1250 centimes
    assert calc.convert_to_chf(10000, 0.125) == 1250


def test_convert_to_chf_rounding():
    # Python round() is banker's (half-to-even): round(166.5) -> 166
    assert calc.convert_to_chf(333, 0.5) == 166


# ---- budget_as_of + expiry ----

def test_budget_as_of_picks_active_row(session):
    c = _cat(session, "Food")
    _budget(session, c.id, 40000, frm=date(2026, 1, 1), to=date(2026, 3, 1))
    _budget(session, c.id, 50000, frm=date(2026, 3, 1))
    assert calc.budget_as_of(session, c.id, date(2026, 2, 1)) == 40000
    assert calc.budget_as_of(session, c.id, date(2026, 4, 1)) == 50000
    assert calc.budget_as_of(session, c.id, date(2025, 12, 1)) is None


# ---- borrow carryover ----

def test_borrow_reduces_next_month_available(session):
    c = _cat(session, "Transport")
    _budget(session, c.id, 10000)  # 100 CHF/month
    _txn(session, date(2026, 6, 15), "borrowing", 3000, cat_id=c.id)  # borrow 30 in June
    # July available = 100 - 30 = 70
    assert calc.available_for_month(session, c.id, 2026, 7) == 7000
    # June available unaffected by its own borrowing
    assert calc.available_for_month(session, c.id, 2026, 6) == 10000


def test_overspent_flag(session):
    c = _cat(session, "Transport")
    _budget(session, c.id, 10000)
    _txn(session, date(2026, 6, 15), "borrowing", 3000, cat_id=c.id)  # prev month borrow
    _txn(session, date(2026, 7, 10), "spending", 8000, cat_id=c.id)  # 80 spent, avail 70
    assert calc.overspent(session, c.id, 2026, 7) is True
    assert calc.overspent(session, c.id, 2026, 7) is True


def test_borrow_does_not_count_as_spending(session):
    c = _cat(session, "Transport")
    _budget(session, c.id, 10000)
    _txn(session, date(2026, 7, 1), "borrowing", 5000, cat_id=c.id)
    # spending sum excludes borrowing
    assert calc.spent_in_month(session, c.id, 2026, 7) == 0
    assert calc.borrowed_in_month(session, c.id, 2026, 7) == 5000


# ---- savings rate ----

def test_savings_rate_simple(session):
    _txn(session, date(2026, 7, 1), "income", 500000)  # 5000 CHF
    _txn(session, date(2026, 7, 2), "spending", 300000)  # 3000 CHF
    assert calc.savings_rate(session, 2026, 7) == 0.4


def test_savings_rate_excludes_borrowing_and_investment(session):
    _txn(session, date(2026, 7, 1), "income", 500000)
    _txn(session, date(2026, 7, 2), "spending", 300000)
    _txn(session, date(2026, 7, 3), "borrowing", 100000)  # ignored
    _txn(session, date(2026, 7, 4), "investment", 50000)  # ignored
    assert calc.savings_rate(session, 2026, 7) == 0.4


def test_savings_rate_zero_income(session):
    _txn(session, date(2026, 7, 2), "spending", 10000)
    assert calc.savings_rate(session, 2026, 7) is None


def test_savings_rate_rolling(session):
    # month 7: income 5000, spend 3000 -> +2000 saved
    _txn(session, date(2026, 7, 1), "income", 500000)
    _txn(session, date(2026, 7, 2), "spending", 300000)
    # month 6: income 5000, spend 4000
    _txn(session, date(2026, 6, 1), "income", 500000)
    _txn(session, date(2026, 6, 2), "spending", 400000)
    # month 5: income 5000, spend 4500
    _txn(session, date(2026, 5, 1), "income", 500000)
    _txn(session, date(2026, 5, 2), "spending", 450000)
    # 3-mo: income 15000, spend 11500 -> 3500/15000
    assert calc.savings_rate_rolling(session, 2026, 7, months=3) == 3500 / 15000


# ---- budget_vs_actual ----

def test_budget_vs_actual_carries_borrow(session):
    food = _cat(session, "Food")
    trans = _cat(session, "Transport")
    _budget(session, food.id, 50000)
    _budget(session, trans.id, 10000)
    _txn(session, date(2026, 6, 15), "borrowing", 3000, cat_id=trans.id)
    _txn(session, date(2026, 7, 5), "spending", 8000, cat_id=trans.id)
    rows = {r["name_en"]: r for r in calc.budget_vs_actual(session, 2026, 7)}
    assert rows["Transport"]["available"] == 7000
    assert rows["Transport"]["spent"] == 8000
    assert rows["Transport"]["overspent"] is True
    assert rows["Transport"]["borrowed_carried"] == 3000
    assert rows["Food"]["available"] == 50000
    assert rows["Food"]["overspent"] is False


# ---- breakdown ----

def test_category_breakdown_sums_spending(session):
    food = _cat(session, "Food")
    trans = _cat(session, "Transport")
    _txn(session, date(2026, 7, 1), "spending", 2000, cat_id=food.id)
    _txn(session, date(2026, 7, 2), "spending", 3000, cat_id=food.id)
    _txn(session, date(2026, 7, 3), "spending", 5000, cat_id=trans.id)
    _txn(session, date(2026, 7, 4), "income", 9999)  # excluded
    rows = calc.category_breakdown(session, date(2026, 7, 1), date(2026, 8, 1))
    by_name = {r["name_en"]: r["total"] for r in rows}
    assert by_name == {"Food": 5000, "Transport": 5000}


# ---- savings_rate_year ----

def test_savings_rate_year_simple(session):
    _txn(session, date(2026, 1, 5), "income", 500000)
    _txn(session, date(2026, 6, 15), "spending", 300000)
    assert calc.savings_rate_year(session, 2026) == 0.4


def test_savings_rate_year_excludes_borrowing_investment(session):
    _txn(session, date(2026, 2, 1), "income", 500000)
    _txn(session, date(2026, 4, 10), "spending", 300000)
    _txn(session, date(2026, 8, 1), "borrowing", 100000)  # ignored
    _txn(session, date(2026, 9, 1), "investment", 50000)  # ignored
    assert calc.savings_rate_year(session, 2026) == 0.4


def test_savings_rate_year_zero_income(session):
    _txn(session, date(2026, 3, 1), "spending", 10000)
    assert calc.savings_rate_year(session, 2026) is None


# ---- budget_vs_actual_year ----

def test_budget_vs_actual_year_sums_monthly_across_year(session):
    food = _cat(session, "Food", "monthly")
    _budget(session, food.id, 50000)  # 500/month -> 6000/year
    _txn(session, date(2026, 1, 10), "spending", 20000, cat_id=food.id)
    _txn(session, date(2026, 6, 15), "spending", 40000, cat_id=food.id)
    rows = {r["name_en"]: r for r in calc.budget_vs_actual_year(session, 2026)}
    assert rows["Food"]["budget"] == 600000
    assert rows["Food"]["spent"] == 60000
    assert rows["Food"]["overspent"] is False


def test_budget_vs_actual_year_yearly_budget_divided_by_12(session):
    tax = _cat(session, "Tax", "yearly")
    _budget(session, tax.id, 120000)  # 1200/year -> 100/month counted
    _txn(session, date(2026, 4, 1), "spending", 150000, cat_id=tax.id)
    rows = {r["name_en"]: r for r in calc.budget_vs_actual_year(session, 2026)}
    assert rows["Tax"]["budget"] == 120000  # 100*12
    assert rows["Tax"]["spent"] == 150000
    assert rows["Tax"]["overspent"] is True


def test_budget_vs_actual_year_yearly_period_counts_investment(session):
    inv = _cat(session, "Investment", "yearly")
    _budget(session, inv.id, 1000000)  # 10000/year
    _txn(session, date(2026, 3, 10), "investment", 60000, cat_id=inv.id)
    _txn(session, date(2026, 6, 26), "investment", 180000, cat_id=inv.id)
    rows = {r["name_en"]: r for r in calc.budget_vs_actual_year(session, 2026)}
    assert rows["Investment"]["budget"] == 1000000
    assert rows["Investment"]["spent"] == 240000
    assert rows["Investment"]["overspent"] is False


def test_budget_vs_actual_year_monthly_period_excludes_investment(session):
    food = _cat(session, "Food", "monthly")
    _budget(session, food.id, 50000)
    _txn(session, date(2026, 1, 10), "spending", 20000, cat_id=food.id)
    _txn(session, date(2026, 1, 15), "investment", 99000, cat_id=food.id)  # ignored for monthly
    rows = {r["name_en"]: r for r in calc.budget_vs_actual_year(session, 2026)}
    assert rows["Food"]["spent"] == 20000


def test_budget_vs_actual_year_excludes_none_period(session):
    ignored = _cat(session, "Misc", "none")
    _budget(session, ignored.id, 9999999)
    rows = {r["name_en"]: r for r in calc.budget_vs_actual_year(session, 2026)}
    assert "Misc" not in rows


# ---- monthly_summaries ----

def test_monthly_summaries_covers_twelve_months(session):
    _txn(session, date(2026, 1, 5), "income", 500000)
    _txn(session, date(2026, 6, 10), "spending", 300000)
    rows = calc.monthly_summaries(session, 2026)
    assert len(rows) == 12
    by_m = {r["m"]: r for r in rows}
    assert by_m[1]["income"] == 500000
    assert by_m[6]["spending"] == 300000
    assert by_m[2]["income"] == 0
    assert by_m[2]["net"] == 0


# ---- deltas (MoM + YoY) ----

def test_deltas_mom_and_yoy(session):
    _txn(session, date(2026, 6, 5), "spending", 10000)   # Jun
    _txn(session, date(2026, 7, 5), "spending", 15000)   # Jul +50%
    _txn(session, date(2025, 7, 5), "spending", 30000)   # Jul'25 (Jul'26 -50%)
    d = calc.deltas(session, 2026, 7)
    assert d["has_mom"] and d["has_yoy"]
    assert d["mom"]["spending"] == 0.5
    assert d["yoy"]["spending"] == -0.5


def test_deltas_zero_prev_returns_none(session):
    _txn(session, date(2026, 7, 5), "spending", 15000)  # only Jul, no prior
    d = calc.deltas(session, 2026, 7)
    assert d["mom"]["spending"] is None
    assert d["yoy"]["spending"] is None


# ---- recurring_annualized ----

def test_recurring_annualized_excludes_income_and_inactive(session):
    housing = _cat(session, "Housing")
    session.add(Recurring(kind="income", category_id=housing.id, amount=743280,
                          day_of_month=1, valid_from=date(2026, 1, 1)))  # salary
    session.add(Recurring(kind="spending", category_id=housing.id, amount=169500,
                          day_of_month=1, valid_from=date(2026, 1, 1)))  # rent
    session.add(Recurring(kind="spending", category_id=housing.id, amount=3095,
                          day_of_month=1, valid_from=date(2026, 1, 1),
                          valid_to=date(2026, 5, 1)))  # phone, ended
    session.commit()
    r = calc.recurring_annualized(session, on=date(2026, 7, 1))
    assert r["count"] == 1  # only rent active
    assert r["total_annual"] == 169500 * 12
    assert r["items"][0]["monthly"] == 169500


# ---- tag_breakdown ----

def test_tag_breakdown_groups_and_sorts(session):
    food = _cat(session, "Food")
    _txn(session, date(2026, 1, 1), "spending", 5000, cat_id=food.id, tag="trip:x")
    _txn(session, date(2026, 1, 2), "spending", 3000, cat_id=food.id, tag="trip:x")
    _txn(session, date(2026, 1, 3), "spending", 1000, cat_id=food.id, tag="misc")
    _txn(session, date(2026, 1, 4), "spending", 9000, cat_id=food.id)  # no tag
    rows = calc.tag_breakdown(session, date(2026, 1, 1), date(2026, 2, 1))
    assert rows[0] == {"tag": "trip:x", "total": 8000, "count": 2}
    assert rows[1] == {"tag": "misc", "total": 1000, "count": 1}
    assert len(rows) == 2  # untagged excluded


# ---- savings_rate_stats ----

def test_savings_rate_stats_median_and_above_target(session):
    # 3 months: 50%, 20%, 40%
    for m, rate in [(4, 0.5), (5, 0.2), (6, 0.4)]:
        _txn(session, date(2026, m, 1), "income", 100000)
        _txn(session, date(2026, m, 2), "spending", int(100000 * (1 - rate)))
    s = calc.savings_rate_stats(session, 2026, 6, target=0.30, months=3)
    assert s["current"] == 0.4
    assert s["median"] == 0.4
    assert s["best"] == 0.5
    assert s["worst"] == 0.2
    assert s["months_above_target"] == 2
    assert s["months_with_data"] == 3


# ---- spending_volatility ----

def test_spending_volatility_pstdev_and_cv(session):
    # 4 months of spending: 1000, 1000, 2000, 3000
    for m, amt in [(3, 100000), (4, 100000), (5, 200000), (6, 300000)]:
        _txn(session, date(2026, m, 1), "spending", amt)
    v = calc.spending_volatility(session, 2026, 6, months=4)
    assert v["mean"] == 175000
    assert v["min"] == 100000
    assert v["max"] == 300000
    assert v["months"] == 4  # Jun, May, Apr, Mar
    assert v["cv"] > 0.01  # nonzero variance


def test_spending_volatility_drops_trailing_zeros(session):
    # Only Jun has data; Jul onwards empty
    _txn(session, date(2026, 6, 1), "spending", 50000)
    v = calc.spending_volatility(session, 2026, 6, months=3)
    assert v["months"] == 1
    assert v["mean"] == 50000
    assert v["std"] == 0
    assert v["cv"] == 0


# ---- fixed_vs_discretionary ----

def test_fixed_vs_discretionary_split(session):
    housing = _cat(session, "Housing", valid_from=date(2026, 1, 1))
    housing.is_fixed = True
    food = _cat(session, "Food", valid_from=date(2026, 1, 1))
    session.commit()
    _txn(session, date(2026, 2, 1), "spending", 200000, cat_id=housing.id)
    _txn(session, date(2026, 2, 2), "spending", 80000, cat_id=food.id)
    _txn(session, date(2026, 2, 3), "income", 1000000)  # ignored
    r = calc.fixed_vs_discretionary(
        session, date(2026, 2, 1), date(2026, 3, 1)
    )
    assert r["fixed"] == 200000
    assert r["discretionary"] == 80000
    assert r["total"] == 280000
    assert r["fixed_pct"] == 200000 / 280000


# ---- ytd_projection ----

def test_ytd_projection_mid_year(session):
    food = _cat(session, "Food", "monthly")
    _budget(session, food.id, 1200000)  # 12k CHF/year = 1k/month
    # 3 months of spending at 100 CHF/month
    for m in (1, 2, 3):
        _txn(session, date(2026, m, 10), "spending", 10000, cat_id=food.id)
    p = calc.ytd_projection(session, 2026)
    assert p["months_elapsed"] >= 1
    # projected = 30000 * 12 / 3 = 120000 if we're past March
    if p["months_elapsed"] == 3:
        assert p["projected_annual"] == 120000
        cat = {c["name_en"]: c for c in p["by_category"]}["Food"]
        assert cat["spent"] == 30000
        assert cat["projected"] == 120000
        assert cat["budget"] == 1200000
        assert cat["status"] == "on-track"


def test_ytd_projection_complete_year(session):
    food = _cat(session, "Food", "monthly", valid_from=date(2025, 1, 1))
    _budget(session, food.id, 100000, frm=date(2025, 1, 1))  # 1000 CHF/mo = 12000/yr
    for m in range(1, 13):
        _txn(session, date(2025, m, 10), "spending", 150000, cat_id=food.id)  # 1500/mo
    p = calc.ytd_projection(session, 2025)
    assert p["is_complete"] is True
    assert p["projected_annual"] == 1800000  # 18000 CHF actual
    cat = {c["name_en"]: c for c in p["by_category"]}["Food"]
    assert cat["budget"] == 1200000  # 12000 CHF
    assert cat["projected"] == 1800000
    assert cat["status"] == "over"  # 1800k > 1.1 * 1200k
