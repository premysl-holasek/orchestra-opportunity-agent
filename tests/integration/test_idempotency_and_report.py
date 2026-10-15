"""Integration tests for idempotency and the weekly report over a real DB."""
from __future__ import annotations

import main
from app.agents.weekly_report import build_weekly_report
from app.collectors.czech_orchestras import CZECH_ORCHESTRAS
from app.collectors.czech_teaching import CZECH_TEACHING_SOURCES
from app.storage.database import OpportunityEntity

# 2 Muvac + 1 Musical Chairs + one page per curated Czech orchestra/teaching source.
_TOTAL = 2 + 1 + len(CZECH_ORCHESTRAS) + len(CZECH_TEACHING_SOURCES)


def test_second_run_is_idempotent(wired, db):
    main.run()
    first_gemini = wired.gemini_calls
    first_slack = len(wired.slack)

    main.run()  # nothing new: all URLs already stored

    with db() as session:
        count = session.query(OpportunityEntity).count()

    # No duplicate rows, no extra evaluations, no extra notifications.
    assert count == _TOTAL
    assert wired.gemini_calls == first_gemini
    assert len(wired.slack) == first_slack


def test_weekly_report_reflects_pipeline_output(wired, db):
    main.run()

    report = build_weekly_report(days=7)

    # Highest-scoring item (Concertmaster, 100) appears first and key fields
    # extracted by the real evaluator are rendered.
    assert "[100]" in report
    assert "Concertmaster" in report
    assert "Prague" in report
    assert "2026-09-01" in report
    # Items are ordered by score: Concertmaster (100) before any 70 item.
    assert report.index("[100]") < report.index("[70]")
