from datetime import date

from sqlmodel import select

from app.models import Category, Transaction
from app.routes import TxnBulkItem, bulk_upsert_transactions, _resolve_category


def test_resolve_category_creates_if_missing(session):
    cid = _resolve_category(session, "Groceries", date(2026, 7, 1))
    assert cid is not None
    # second call returns same category, no duplicate
    cid2 = _resolve_category(session, "Groceries", date(2026, 7, 2))
    assert cid == cid2
    assert len(session.exec(select(Category)).all()) == 1


def test_resolve_category_matches_zh_name(session):
    session.add(Category(
        name_en="Food", name_zh="食物", budget_period="monthly", valid_from=date(2026, 1, 1)
    ))
    session.commit()
    cid = _resolve_category(session, "食物", date(2026, 7, 1))
    assert cid == 1
    assert len(session.exec(select(Category)).all()) == 1  # no new row


def test_bulk_insert_then_upsert_by_external_id(session):
    items1 = [
        TxnBulkItem(occurred_on=date(2026, 7, 1), kind="spending", amount=1000,
                    category_name="Food", external_id="r1"),
        TxnBulkItem(occurred_on=date(2026, 7, 2), kind="spending", amount=2000,
                    category_name="Transport", external_id="r2"),
    ]
    r1 = bulk_upsert_transactions(session, items1)
    assert r1 == {"created": 2, "updated": 0}
    assert len(session.exec(select(Transaction)).all()) == 2

    # re-run with updated amount on r1, new amount on r2 unchanged, plus a new row
    items2 = [
        TxnBulkItem(occurred_on=date(2026, 7, 1), kind="spending", amount=1500,
                    category_name="Food", external_id="r1"),
        TxnBulkItem(occurred_on=date(2026, 7, 3), kind="spending", amount=500,
                    category_name="Food", external_id="r3"),
    ]
    r2 = bulk_upsert_transactions(session, items2)
    assert r2 == {"created": 1, "updated": 1}
    txns = {t.external_id: t for t in session.exec(select(Transaction)).all()}
    assert txns["r1"].amount == 1500  # updated
    assert txns["r2"].amount == 2000  # untouched
    assert txns["r3"].amount == 500   # new


def test_bulk_without_external_id_always_inserts(session):
    items = [
        TxnBulkItem(occurred_on=date(2026, 7, 1), kind="spending", amount=1000,
                    category_name="Food"),
        TxnBulkItem(occurred_on=date(2026, 7, 1), kind="spending", amount=1000,
                    category_name="Food"),
    ]
    r = bulk_upsert_transactions(session, items)
    assert r == {"created": 2, "updated": 0}
    assert len(session.exec(select(Transaction)).all()) == 2
