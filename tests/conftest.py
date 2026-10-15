"""Shared pytest fixtures."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents import weekly_report
from app.models import Evaluation, Opportunity
from app.storage import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Provide an isolated, file-backed SQLite database for a test.

    Patches the module-level ``engine``/``SessionLocal`` used by the storage
    layer (and the report agent) so production code paths hit the test DB.
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    test_session = sessionmaker(
        bind=engine, future=True, expire_on_commit=False
    )
    database.Base.metadata.create_all(engine)

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", test_session)
    monkeypatch.setattr(weekly_report, "SessionLocal", test_session)

    return test_session


@pytest.fixture
def sample_opportunity() -> Opportunity:
    return Opportunity(
        source="muvac",
        title="First Violin Audition",
        organization="Czech Philharmonic",
        url="https://example.com/jobs/1",
        content="We are looking for a first violinist.",
    )


@pytest.fixture
def sample_evaluation() -> Evaluation:
    return Evaluation(
        position="First Violin",
        orchestra="Czech Philharmonic",
        city="Prague",
        country="CZ",
        deadline="2026-09-01",
        score=85,
        summary="Konkurz na první housle.",
    )
