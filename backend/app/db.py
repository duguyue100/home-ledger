import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = "data/ledger.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


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


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
