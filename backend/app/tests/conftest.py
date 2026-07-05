from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def session() -> Iterator[Session]:
    """Fresh in-memory DB per test. calc/schema functions take this session."""
    from app import models  # noqa: F401 — register on metadata

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
