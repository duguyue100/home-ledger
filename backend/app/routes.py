"""HTTP routes: CRUD, bulk import, recurring materialize, aggregates.

Aggregates are thin wrappers over app.calc. Request schemas are plain Pydantic
models (not table models) so create/update shapes stay explicit.
"""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app import calc
from app.db import get_session
from app.models import Budget, Category, Recurring, Transaction

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---- schemas ----

class CategoryCreate(BaseModel):
    name_en: str
    name_zh: str | None = None
    budget_period: str = "monthly"
    valid_from: date
    valid_to: date | None = None


class CategoryPatch(BaseModel):
    name_zh: str | None = None
    valid_to: date | None = None  # set to expire


class BudgetCreate(BaseModel):
    category_id: int
    amount: int
    valid_from: date
    valid_to: date | None = None


class RecurringCreate(BaseModel):
    kind: str
    category_id: int | None = None
    amount: int
    currency: str = "CHF"
    day_of_month: int
    valid_from: date
    valid_to: date | None = None
    note_en: str | None = None
    note_zh: str | None = None


class TransactionCreate(BaseModel):
    occurred_on: date
    kind: str
    category_id: int | None = None
    amount: int
    currency: str = "CHF"
    original_amount: int | None = None
    original_currency: str | None = None
    note: str | None = None
    tag: str | None = None
    source_recurring_id: int | None = None
    external_id: str | None = None


class TransactionPatch(BaseModel):
    occurred_on: date | None = None
    kind: str | None = None
    category_id: Optional[int] = None
    amount: int | None = None
    currency: str | None = None
    original_amount: Optional[int] = None
    original_currency: str | None = None
    note: str | None = None
    tag: str | None = None
    external_id: str | None = None


class TxnBulkItem(BaseModel):
    occurred_on: date
    kind: str
    amount: int
    currency: str = "CHF"
    original_amount: int | None = None
    original_currency: str | None = None
    note: str | None = None
    tag: str | None = None
    category_name: str | None = None
    external_id: str | None = None


# ---- categories ----

@router.get("/categories")
def list_categories(active_only: bool = False, session: Session = Depends(get_session)):
    q = select(Category)
    if active_only:
        q = q.where((Category.valid_to == None) | (Category.valid_to > date.today()))  # noqa: E711
    return session.exec(q.order_by(Category.name_en)).all()


@router.post("/categories")
def create_category(body: CategoryCreate, session: Session = Depends(get_session)):
    c = Category(**body.model_dump())
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.patch("/categories/{cid}")
def patch_category(cid: int, body: CategoryPatch, session: Session = Depends(get_session)):
    c = session.get(Category, cid)
    if not c:
        raise HTTPException(404, "category not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.delete("/categories/{cid}")
def delete_category(cid: int, session: Session = Depends(get_session)):
    c = session.get(Category, cid)
    if not c:
        raise HTTPException(404, "category not found")
    if session.exec(select(Transaction).where(Transaction.category_id == cid)).first():
        raise HTTPException(409, "category has transactions; cannot delete")
    if session.exec(select(Recurring).where(Recurring.category_id == cid)).first():
        raise HTTPException(409, "category in use by a recurring; remove it first")
    for b in session.exec(select(Budget).where(Budget.category_id == cid)).all():
        session.delete(b)
    session.delete(c)
    session.commit()
    return {"ok": True}


@router.post("/categories/bulk")
def bulk_categories(items: list[CategoryCreate], session: Session = Depends(get_session)):
    created = updated = 0
    for it in items:
        existing = session.exec(
            select(Category).where(Category.name_en == it.name_en)
        ).first()
        if existing:
            existing.name_zh = it.name_zh or existing.name_zh
            existing.budget_period = it.budget_period
            existing.valid_from = it.valid_from
            existing.valid_to = it.valid_to
            session.add(existing)
            updated += 1
        else:
            session.add(Category(**it.model_dump()))
            created += 1
    session.commit()
    return {"created": created, "updated": updated}


# ---- budgets ----

@router.get("/budgets")
def list_budgets(category_id: int | None = None, as_of: date | None = None,
                 session: Session = Depends(get_session)):
    if as_of is not None and category_id is not None:
        amt = calc.budget_as_of(session, category_id, as_of)
        return {"category_id": category_id, "as_of": as_of, "amount": amt}
    q = select(Budget)
    if category_id is not None:
        q = q.where(Budget.category_id == category_id)
    return session.exec(q.order_by(Budget.valid_from.desc())).all()


@router.post("/budgets")
def create_budget(body: BudgetCreate, session: Session = Depends(get_session)):
    # expire any overlapping budget for the same category
    overlap = session.exec(
        select(Budget).where(Budget.category_id == body.category_id)
        .where((Budget.valid_to == None) | (Budget.valid_to > body.valid_from))  # noqa: E711
    ).all()
    for b in overlap:
        b.valid_to = body.valid_from
        session.add(b)
    b = Budget(**body.model_dump())
    session.add(b)
    session.commit()
    session.refresh(b)
    return b


@router.delete("/budgets/{bid}")
def delete_budget(bid: int, session: Session = Depends(get_session)):
    b = session.get(Budget, bid)
    if not b:
        raise HTTPException(404, "budget not found")
    session.delete(b)
    session.commit()
    return {"ok": True}


@router.post("/budgets/bulk")
def bulk_budgets(items: list[BudgetCreate], session: Session = Depends(get_session)):
    created = updated = 0
    for it in items:
        existing = session.exec(
            select(Budget).where(Budget.category_id == it.category_id)
            .where((Budget.valid_to == None) | (Budget.valid_to > it.valid_from))  # noqa: E711
        ).first()
        if existing:
            existing.valid_to = it.valid_from
            existing.amount = it.amount
            session.add(existing)
            updated += 1
        else:
            session.add(Budget(**it.model_dump()))
            created += 1
    session.commit()
    return {"created": created, "updated": updated}


# ---- recurring ----

@router.get("/recurring")
def list_recurring(active_only: bool = False, session: Session = Depends(get_session)):
    q = select(Recurring)
    if active_only:
        q = q.where((Recurring.valid_to == None) | (Recurring.valid_to > date.today()))  # noqa: E711
    return session.exec(q.order_by(Recurring.valid_from.desc())).all()


@router.post("/recurring")
def create_recurring(body: RecurringCreate, session: Session = Depends(get_session)):
    r = Recurring(**body.model_dump())
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


class RecurringPatch(BaseModel):
    valid_to: date | None = None


@router.patch("/recurring/{rid}")
def patch_recurring(rid: int, body: RecurringPatch, session: Session = Depends(get_session)):
    r = session.get(Recurring, rid)
    if not r:
        raise HTTPException(404, "recurring not found")
    r.valid_to = body.valid_to
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


@router.post("/recurring/{rid}/materialize")
def materialize(rid: int, on: date, amount_override: int | None = None,
                session: Session = Depends(get_session)):
    r = session.get(Recurring, rid)
    if not r:
        raise HTTPException(404, "recurring not found")
    if r.valid_to is not None and on >= r.valid_to:
        raise HTTPException(409, "recurring expired for this date")
    if on < r.valid_from:
        raise HTTPException(409, "date before recurring valid_from")
    # don't double-post same recurring for the same month
    s, e = calc.month_bounds(on.year, on.month)
    dup = session.exec(
        select(Transaction).where(Transaction.source_recurring_id == rid)
        .where(Transaction.occurred_on >= s).where(Transaction.occurred_on < e)
    ).first()
    if dup:
        raise HTTPException(409, "already materialized for this month")
    t = Transaction(
        occurred_on=on,
        kind=r.kind,
        category_id=r.category_id,
        amount=amount_override if amount_override is not None else r.amount,
        currency=r.currency,
        source_recurring_id=rid,
        note=r.note_en,  # snapshot note at materialize time
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@router.delete("/recurring/{rid}")
def delete_recurring(rid: int, session: Session = Depends(get_session)):
    r = session.get(Recurring, rid)
    if not r:
        raise HTTPException(404, "recurring not found")
    for t in session.exec(select(Transaction).where(Transaction.source_recurring_id == rid)).all():
        t.source_recurring_id = None
        session.add(t)
    session.delete(r)
    session.commit()
    return {"ok": True}


@router.post("/recurring/materialize-due")
def materialize_due(on: date, session: Session = Depends(get_session)):
    """Post all active recurring templates due for the month of `on` that
    haven't already been materialized that month."""
    s, e = calc.month_bounds(on.year, on.month)
    recurrings = session.exec(
        select(Recurring)
        .where(Recurring.valid_from <= on)
        .where((Recurring.valid_to == None) | (Recurring.valid_to > on))  # noqa: E711
    ).all()
    posted: list[int] = []
    for r in recurrings:
        if on < r.valid_from:
            continue
        dup = session.exec(
            select(Transaction).where(Transaction.source_recurring_id == r.id)
            .where(Transaction.occurred_on >= s).where(Transaction.occurred_on < e)
        ).first()
        if dup:
            continue
        t = Transaction(
            occurred_on=on,
            kind=r.kind,
            category_id=r.category_id,
            amount=r.amount,
            currency=r.currency,
            source_recurring_id=r.id,
            note=r.note_en,
        )
        session.add(t)
        posted.append(r.id)
    session.commit()
    return {"posted": posted}


@router.post("/recurring/bulk")
def bulk_recurring(items: list[RecurringCreate], session: Session = Depends(get_session)):
    created = 0
    for it in items:
        session.add(Recurring(**it.model_dump()))
        created += 1
    session.commit()
    return {"created": created}


# ---- transactions CRUD ----

@router.get("/transactions")
def list_transactions(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    kind: list[str] | None = Query(None),
    category_id: int | None = None,
    tag: str | None = None,
    currency: str | None = None,
    recurring: bool | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = select(Transaction)
    if from_date:
        stmt = stmt.where(Transaction.occurred_on >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.occurred_on < to_date)
    if kind:
        stmt = stmt.where(Transaction.kind.in_(kind))
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if tag:
        stmt = stmt.where(Transaction.tag == tag)
    if currency:
        stmt = stmt.where(Transaction.currency == currency)
    if recurring is True:
        stmt = stmt.where(Transaction.source_recurring_id != None)  # noqa: E711
    elif recurring is False:
        stmt = stmt.where(Transaction.source_recurring_id == None)  # noqa: E711
    if q:
        stmt = stmt.where(Transaction.note.contains(q))
    return session.exec(
        stmt.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
        .limit(limit).offset(offset)
    ).all()


@router.post("/transactions")
def create_transaction(body: TransactionCreate, session: Session = Depends(get_session)):
    t = Transaction(**body.model_dump())
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@router.get("/transactions/{tid}")
def get_transaction(tid: int, session: Session = Depends(get_session)):
    t = session.get(Transaction, tid)
    if not t:
        raise HTTPException(404, "transaction not found")
    return t


@router.patch("/transactions/{tid}")
def patch_transaction(tid: int, body: TransactionPatch,
                      session: Session = Depends(get_session)):
    t = session.get(Transaction, tid)
    if not t:
        raise HTTPException(404, "transaction not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@router.delete("/transactions/{tid}")
def delete_transaction(tid: int, session: Session = Depends(get_session)):
    t = session.get(Transaction, tid)
    if not t:
        raise HTTPException(404, "transaction not found")
    session.delete(t)
    session.commit()
    return {"deleted": tid}


# ---- transactions bulk (spreadsheet ingestion) ----

def _resolve_category(session: Session, name: str, on: date) -> int:
    """Find active category by name_en or name_zh; create if missing."""
    c = session.exec(
        select(Category)
        .where((Category.name_en == name) | (Category.name_zh == name))
        .where((Category.valid_to == None) | (Category.valid_to > on))  # noqa: E711
    ).first()
    if c:
        return c.id
    c = Category(name_en=name, budget_period="monthly", valid_from=on)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c.id


def bulk_upsert_transactions(session: Session, items: list[TxnBulkItem]) -> dict:
    """Insert or update by external_id; resolve category by name (creating if missing)."""
    created = updated = 0
    for it in items:
        cat_id = None
        if it.category_name:
            cat_id = _resolve_category(session, it.category_name, it.occurred_on)
        data = it.model_dump(exclude={"category_name"})
        data["category_id"] = cat_id
        if it.external_id:
            existing = session.exec(
                select(Transaction).where(Transaction.external_id == it.external_id)
            ).first()
            if existing:
                for k, v in data.items():
                    if v is not None or k in ("amount", "occurred_on", "kind"):
                        setattr(existing, k, v)
                session.add(existing)
                updated += 1
                continue
        session.add(Transaction(**data))
        created += 1
    session.commit()
    return {"created": created, "updated": updated}


@router.post("/transactions/bulk")
def bulk_transactions(items: list[TxnBulkItem], session: Session = Depends(get_session)):
    return bulk_upsert_transactions(session, items)


# ---- aggregates ----

@router.get("/summary")
def summary(period: str, d: date, session: Session = Depends(get_session)):
    if period == "day":
        s, e = calc.day_bounds(d)
    elif period == "month":
        s, e = calc.month_bounds(d.year, d.month)
    elif period == "year":
        s, e = calc.year_bounds(d.year)
    else:
        raise HTTPException(400, "period must be day|month|year")
    return calc.summary(session, s, e)


@router.get("/breakdown")
def breakdown(from_date: date = Query(..., alias="from"),
             to_date: date = Query(..., alias="to"),
             session: Session = Depends(get_session)):
    return calc.category_breakdown(session, from_date, to_date)


@router.get("/budget-vs-actual")
def budget_vs_actual(year: int, month: int, session: Session = Depends(get_session)):
    return calc.budget_vs_actual(session, year, month)


@router.get("/savings-rate")
def savings_rate(year: int, month: int, roll: int = 0,
                 session: Session = Depends(get_session)):
    if roll:
        return {"rate": calc.savings_rate_rolling(session, year, month, roll)}
    return {"rate": calc.savings_rate(session, year, month)}


@router.get("/report")
def report(
    month: date | None = Query(None),
    ref: date | None = Query(None),
    period: Literal["month", "year"] = "month",
    roll: int = 0,
    session: Session = Depends(get_session),
):
    """Period report. `ref` is the month (day-of-month ignored) or year anchor.

    The legacy `month` query alias still works for back-compat with monthly
    callers and tests.
    """
    r = ref or month
    if r is None:
        raise HTTPException(422, "ref (or month) is required")
    if period == "month":
        s, e = calc.month_bounds(r.year, r.month)
        return {
            "period": "month",
            "ref": r,
            "summary": calc.summary(session, s, e),
            "breakdown": calc.category_breakdown(session, s, e),
            "budget_vs_actual": calc.budget_vs_actual(session, r.year, r.month),
            "savings_rate": calc.savings_rate(session, r.year, r.month),
            "savings_rate_rolling": calc.savings_rate_rolling(
                session, r.year, r.month, months=6 if not roll else roll
            ),
        }
    # yearly
    s, e = calc.year_bounds(r.year)
    return {
        "period": "year",
        "ref": r,
        "year": r.year,
        "summary": calc.summary(session, s, e),
        "breakdown": calc.category_breakdown(session, s, e),
        "budget_vs_actual": calc.budget_vs_actual_year(session, r.year),
        "savings_rate": calc.savings_rate_year(session, r.year),
        "savings_rate_rolling": calc.savings_rate_rolling(
            session, r.year, 12, months=12
        ),
        "monthly": calc.monthly_summaries(session, r.year),
    }
