"""End-to-end integration test of the full collection pipeline."""
from __future__ import annotations

import main
from app.collectors.czech_orchestras import CZECH_ORCHESTRAS
from app.collectors.czech_teaching import CZECH_TEACHING_SOURCES
from app.storage.database import OpportunityEntity

# 2 Muvac + 1 Musical Chairs + one page per curated Czech orchestra/teaching source.
_TOTAL = 2 + 1 + len(CZECH_ORCHESTRAS) + len(CZECH_TEACHING_SOURCES)


def test_full_run_collects_evaluates_stores_and_notifies(wired, db):
    main.run()

    # Every collected opportunity is evaluated exactly once.
    assert wired.gemini_calls == _TOTAL

    with db() as session:
        rows = session.query(OpportunityEntity).all()
    assert len(rows) == _TOTAL

    # Every stored row went through the real evaluator and got structured data.
    assert all(r.summary == "Integrační shrnutí." for r in rows)
    assert all(r.score in {70, 90, 100} for r in rows)

    # The Tutti listing (score 70) is below MIN_SCORE and is not notified;
    # everything else is notified via both Slack and email.
    assert len(wired.slack) == _TOTAL - 1
    assert len(wired.emails) == _TOTAL - 1

    # The Concertmaster (score 100) produced a notification.
    assert any("Concertmaster" in msg for msg in wired.slack)
    # The Tutti opportunity is stored but never notified.
    assert not any("Tutti" in msg for msg in wired.slack)


def test_full_run_persists_real_parsed_fields(wired, db):
    main.run()

    with db() as session:
        concertmaster = (
            session.query(OpportunityEntity)
            .filter(OpportunityEntity.position == "Concertmaster")
            .one()
        )

    assert concertmaster.score == 100
    assert concertmaster.city == "Prague"
    assert concertmaster.country == "CZ"
    assert concertmaster.deadline == "2026-09-01"
    assert concertmaster.source == "muvac"
    assert concertmaster.url.endswith("/en/vacancy/berlin-philharmonic-101")
