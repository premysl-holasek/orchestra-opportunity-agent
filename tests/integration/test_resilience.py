"""Integration tests for pipeline resilience to external failures."""
from __future__ import annotations

from google.genai import errors as genai_errors

import main
from app.agents import evaluator
from app.collectors import base as collectors_base
from app.collectors.czech_orchestras import CZECH_ORCHESTRAS
from app.collectors.czech_teaching import CZECH_TEACHING_SOURCES
from app.storage.database import OpportunityEntity
from tests.integration.conftest import _FakeHTTPResponse, _route

# 2 Muvac + 1 Musical Chairs + one page per curated Czech orchestra/teaching source.
_TOTAL = 2 + 1 + len(CZECH_ORCHESTRAS) + len(CZECH_TEACHING_SOURCES)


def test_run_survives_a_failing_collector(wired, db, monkeypatch):
    def flaky_get(url, **kwargs):
        if "muvac.com" in url:
            raise ConnectionError("muvac down")
        return _FakeHTTPResponse(_route(url))

    monkeypatch.setattr(collectors_base.requests, "get", flaky_get)

    # Should not raise even though one source is completely unavailable.
    main.run()

    with db() as session:
        rows = session.query(OpportunityEntity).all()

    # Muvac's 2 items are gone; Musical Chairs (1) + orchestras remain.
    assert len(rows) == _TOTAL - 2
    assert all(r.source != "muvac" for r in rows)


def test_run_survives_persistent_gemini_errors(wired, db, monkeypatch):
    class _AlwaysFailingModels:
        def generate_content(self, *, model, contents, config):
            raise genai_errors.APIError(
                503, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}}
            )

    class _AlwaysFailingClient:
        models = _AlwaysFailingModels()

    monkeypatch.setattr(evaluator, "_client", lambda: _AlwaysFailingClient())

    # Evaluation degrades gracefully to empty results; the run completes.
    main.run()

    with db() as session:
        rows = session.query(OpportunityEntity).all()

    # All opportunities are still stored, but with empty evaluations.
    assert len(rows) == _TOTAL
    assert all(r.score == 0 for r in rows)
    assert all((r.position or "") == "" for r in rows)

    # Nothing reaches the notification threshold.
    assert wired.slack == []
    assert wired.emails == []
