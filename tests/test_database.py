"""Tests for the SQLite persistence layer."""
from __future__ import annotations

from app.storage import database
from app.storage.database import OpportunityEntity


def test_init_db_creates_table(db):
    database.init_db()  # idempotent; table already created by fixture
    assert "opportunities" in database.Base.metadata.tables


def test_save_persists_opportunity_and_evaluation(
    db, sample_opportunity, sample_evaluation
):
    entity = database.save(sample_opportunity, sample_evaluation)

    assert entity.id is not None
    assert entity.url == sample_opportunity.url
    assert entity.source == "muvac"
    assert entity.position == "First Violin"
    assert entity.orchestra == "Czech Philharmonic"
    assert entity.score == 85
    assert entity.summary == "Konkurz na první housle."


def test_exists_false_when_absent(db):
    assert database.exists("https://example.com/none") is False


def test_exists_true_after_save(db, sample_opportunity, sample_evaluation):
    database.save(sample_opportunity, sample_evaluation)
    assert database.exists(sample_opportunity.url) is True


def test_save_stores_created_at(db, sample_opportunity, sample_evaluation):
    database.save(sample_opportunity, sample_evaluation)
    with db() as session:
        row = session.query(OpportunityEntity).one()
    assert row.created_at is not None
