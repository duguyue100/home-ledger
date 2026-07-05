from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: int | None = Field(default=None, primary_key=True)
    name_en: str
    name_zh: str | None = None
    budget_period: str = Field(default="monthly")  # 'monthly' | 'yearly' | 'none'
    valid_from: date
    valid_to: date | None = None  # NULL = active; exclusive end
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"

    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="categories.id", index=True)
    amount: int  # CHF minor units
    valid_from: date
    valid_to: date | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Recurring(SQLModel, table=True):
    __tablename__ = "recurring"

    id: int | None = Field(default=None, primary_key=True)
    kind: str  # 'income' | 'spending' | 'investment'
    category_id: int | None = Field(default=None, foreign_key="categories.id")
    amount: int  # minor units
    currency: str = Field(default="CHF")
    day_of_month: int  # 1..28
    valid_from: date
    valid_to: date | None = None
    note_en: str | None = None
    note_zh: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    occurred_on: date = Field(index=True)
    kind: str = Field(index=True)  # 'income'|'spending'|'investment'|'borrowing'
    category_id: int | None = Field(default=None, foreign_key="categories.id", index=True)
    amount: int  # CHF minor units (converted)
    currency: str = Field(default="CHF")
    original_amount: int | None = None
    original_currency: str | None = None
    note: str | None = None
    tag: str | None = None
    source_recurring_id: int | None = Field(default=None, foreign_key="recurring.id")
    external_id: str | None = Field(default=None, unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
