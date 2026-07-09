import os
from collections.abc import Iterator

from sqlalchemy import bindparam, text
from sqlmodel import Session, SQLModel, create_engine

DB_PATH = "data/ledger.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

_FIXED_DEFAULT_NAMES = ("Housing", "Insurance", "Communication", "Transportation")


def _migrate(session: Session) -> None:
    """Idempotent schema + data migrations for live DBs.

    create_all only adds NEW tables; it does not add columns to existing ones.
    So we ALTER TABLE for new columns, guarded by a pragma check.
    """
    cols = {r[1] for r in session.execute(text("PRAGMA table_info(categories)"))}
    if "is_fixed" not in cols:
        session.execute(text("ALTER TABLE categories ADD COLUMN is_fixed INTEGER NOT NULL DEFAULT 0"))
        session.execute(
            text("UPDATE categories SET is_fixed=1 WHERE name_en IN :names").bindparams(
                bindparam("names", expanding=True)
            ),
            {"names": _FIXED_DEFAULT_NAMES},
        )
        session.commit()


def init_db() -> None:
    """Create the data dir + all tables. Uses the current DB_PATH (tests may swap it)."""
    from app import models  # noqa: F401 — register tables on metadata

    global engine
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _migrate(session)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
