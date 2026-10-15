"""Tests for the weekly report builder."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.agents.weekly_report import build_weekly_report
from app.storage.database import OpportunityEntity


def _insert(session_factory, **overrides):
    defaults = {
        "url": "https://e/1",
        "source": "muvac",
        "title": "Title",
        "organization": "Org",
        "position": "First Violin",
        "orchestra": "Czech Philharmonic",
        "city": "Prague",
        "country": "CZ",
        "deadline": "2026-09-01",
        "score": 90,
        "summary": "Shrnutí.",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    with session_factory() as session:
        session.add(OpportunityEntity(**defaults))
        session.commit()


def test_report_message_when_empty(db):
    report = build_weekly_report()
    assert "nebyly nalezeny" in report


def test_report_lists_recent_items(db):
    _insert(db, url="https://e/1", position="First Violin", score=88)
    report = build_weekly_report(days=7)

    assert "First Violin" in report
    assert "Czech Philharmonic" in report
    assert "[88]" in report
    assert "Prague" in report
    assert "2026-09-01" in report
    assert "https://e/1" in report
    assert "Shrnutí." in report


def test_report_excludes_old_items(db):
    old = datetime.now(UTC) - timedelta(days=30)
    _insert(db, url="https://old", created_at=old, position="Old Violin")
    report = build_weekly_report(days=7)
    assert "Old Violin" not in report


def test_report_orders_by_score_desc(db):
    _insert(db, url="https://low", score=70, position="Low")
    _insert(db, url="https://high", score=95, position="High")
    report = build_weekly_report(days=7)
    assert report.index("High") < report.index("Low")
