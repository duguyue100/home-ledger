import sqlite3
from datetime import date

import pytest
from sqlmodel import select

from app.db import init_db
from app.models import Budget, Category, Transaction


def test_init_db_creates_all_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("app.db.DB_PATH", str(db_file))
    init_db()
    con = sqlite3.connect(db_file)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"categories", "budgets", "recurring", "transactions"} <= tables


def test_external_id_unique(session):
    session.add(Transaction(
        occurred_on=date(2026, 7, 1), kind="spending", amount=100, external_id="row-1",
    ))
    session.add(Transaction(
        occurred_on=date(2026, 7, 2), kind="spending", amount=200, external_id="row-1",
    ))
    with pytest.raises(Exception):
        session.commit()


def test_valid_from_to_roundtrip(session):
    cat = Category(name_en="Food", valid_from=date(2026, 1, 1), valid_to=date(2026, 6, 1))
    bud = Budget(category_id=1, amount=50000, valid_from=date(2026, 1, 1))
    session.add(cat)
    session.add(bud)
    session.commit()
    assert session.exec(select(Category)).one().name_en == "Food"
    assert session.exec(select(Budget)).one().amount == 50000
