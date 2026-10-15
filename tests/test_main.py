"""Tests for the main orchestration flow."""
from __future__ import annotations

import main
from app.collectors.czech_orchestras import CzechOrchestrasCollector
from app.collectors.czech_teaching import CzechTeachingCollector
from app.collectors.musicalchairs import MusicalChairsCollector
from app.collectors.muvac import MuvacCollector
from app.models import Evaluation, Opportunity


def _opp(url: str) -> Opportunity:
    return Opportunity(
        source="muvac",
        title="t",
        organization="o",
        url=url,
        content="c",
    )


def test_get_collectors_returns_all_sources():
    collectors = main.get_collectors()
    types = {type(c) for c in collectors}
    assert types == {
        MuvacCollector,
        MusicalChairsCollector,
        CzechOrchestrasCollector,
        CzechTeachingCollector,
    }


def test_notify_sends_slack_and_email(monkeypatch):
    slack_calls = []
    email_calls = []
    monkeypatch.setattr(main, "send_slack", lambda msg: slack_calls.append(msg))
    monkeypatch.setattr(
        main, "send_email", lambda subj, body: email_calls.append((subj, body))
    )

    opp = _opp("https://e/1")
    ev = Evaluation(position="First Violin", orchestra="CP", score=90)
    main.notify(opp, ev)

    assert len(slack_calls) == 1
    assert len(email_calls) == 1
    subject, body = email_calls[0]
    assert "First Violin" in subject
    assert "90" in body


class _FakeCollector:
    source = "fake"

    def __init__(self, items):
        self._items = items

    def safe_collect(self):
        return self._items


def test_run_processes_new_and_notifies_high_scores(monkeypatch):
    new_opp = _opp("https://e/new")
    dup_opp = _opp("https://e/dup")

    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(
        main, "get_collectors", lambda: [_FakeCollector([new_opp, dup_opp])]
    )
    monkeypatch.setattr(
        main, "exists", lambda url: url == "https://e/dup"
    )

    saved = []
    monkeypatch.setattr(main, "save", lambda opp, ev: saved.append((opp, ev)))

    monkeypatch.setattr(
        main, "evaluate", lambda opp: Evaluation(position="First Violin", score=90)
    )

    notified = []
    monkeypatch.setattr(
        main, "notify", lambda opp, ev: notified.append(opp.url)
    )
    monkeypatch.setattr(main.settings, "min_score", 80)

    main.run()

    # Only the new opportunity is processed (duplicate skipped).
    assert len(saved) == 1
    assert saved[0][0].url == "https://e/new"
    assert notified == ["https://e/new"]


def test_run_skips_notification_below_min_score(monkeypatch):
    opp = _opp("https://e/low")

    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "get_collectors", lambda: [_FakeCollector([opp])])
    monkeypatch.setattr(main, "exists", lambda url: False)
    monkeypatch.setattr(main, "save", lambda opp, ev: None)
    monkeypatch.setattr(main, "evaluate", lambda opp: Evaluation(score=10))

    notified = []
    monkeypatch.setattr(main, "notify", lambda opp, ev: notified.append(opp.url))
    monkeypatch.setattr(main.settings, "min_score", 80)

    main.run()

    assert notified == []
