"""Fixtures wiring real components together with mocked external boundaries.

Integration tests exercise the real pipeline (collectors -> evaluator ->
storage -> notifications) and only stub the true edges of the system:
outbound HTTP for scraping, the Gemini client, the Slack webhook and SMTP.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from app.agents import evaluator
from app.collectors import base as collectors_base
from app.collectors.czech_orchestras import CZECH_ORCHESTRAS
from app.collectors.czech_teaching import CZECH_TEACHING_SOURCES
from app.notifications import email as email_mod
from app.notifications import slack as slack_mod
from config import settings

# --- Fake outbound HTTP for collectors ------------------------------------

class _FakeHTTPResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return json.loads(self.text)


# Muvac is a JavaScript SPA served by a JSON API; orchestra pages return a
# title + body that the evaluator will score.
_MUVAC_JSON = json.dumps(
    {
        "data": {
            "items": [
                {
                    "title": "Concertmaster – Berlin Philharmonic",
                    "customSlug": "berlin-philharmonic-101",
                    "expertises": [{"group": "instruments.violin"}],
                    "profile": {
                        "name": "Berlin Philharmonic",
                        "city": "Berlin",
                        "countryCode": "de",
                    },
                },
                {
                    "title": "Tutti Violin – Munich",
                    "customSlug": "munich-102",
                    "expertises": [{"group": "instruments.violin"}],
                    "profile": {
                        "name": "Munich Orchestra",
                        "city": "Munich",
                        "countryCode": "de",
                    },
                },
                {
                    "title": "Solo Horn – ignored",
                    "customSlug": "horn-103",
                    "expertises": [{"group": "instruments.horn"}],
                    "profile": {"name": "Some Orchestra"},
                },
            ]
        }
    }
)

_MUSICALCHAIRS_HTML = """
<html><body>
  <a href="/violin/jobs/201">First Violin – Czech Philharmonic</a>
  <a href="/violin/jobs/201">First Violin – duplicate</a>
</body></html>
"""

_ORCHESTRA_HTML = """
<html><head><title>Auditions {org}</title></head>
<body>First violin audition for {org}. Apply by 2026-09-01.</body></html>
"""


def _route(url: str) -> str:
    if "muvac.com" in url:
        return _MUVAC_JSON
    if "musicalchairs.info" in url:
        return _MUSICALCHAIRS_HTML
    # Curated orchestra and teaching pages.
    for entry in (*CZECH_ORCHESTRAS, *CZECH_TEACHING_SOURCES):
        if entry["url"] == url:
            return _ORCHESTRA_HTML.format(org=entry["organization"])
    return "<html><body>unknown</body></html>"


# --- Fake Gemini client ----------------------------------------------------

class _FakeGeminiResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeGeminiModels:
    def __init__(self, holder):
        self._holder = holder

    def generate_content(self, *, model, contents, config):
        self._holder.gemini_calls += 1
        lowered = contents.lower()
        if "tutti" in lowered:
            score, position = 70, "Tutti Violin"
        elif "concertmaster" in lowered:
            score, position = 100, "Concertmaster"
        else:
            score, position = 90, "First Violin"
        payload = {
            "position": position,
            "orchestra": "Test Orchestra",
            "city": "Prague",
            "country": "CZ",
            "deadline": "2026-09-01",
            "score": score,
            "summary": "Integrační shrnutí.",
        }
        return _FakeGeminiResponse(json.dumps(payload))


class _FakeGeminiClient:
    def __init__(self, holder):
        self.models = _FakeGeminiModels(holder)


# --- Fake SMTP -------------------------------------------------------------

class _FakeSMTP:
    def __init__(self, holder, host, port):
        self._holder = holder
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        return None

    def send_message(self, msg):
        self._holder.emails.append(
            {"subject": msg["Subject"], "to": msg["To"]}
        )


@dataclass
class Captured:
    """Collects everything the pipeline emitted at its external edges."""

    slack: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    gemini_calls: int = 0


@pytest.fixture
def wired(db, monkeypatch):
    """Wire the full pipeline with mocked edges; yields a ``Captured`` holder.

    ``db`` (from tests/conftest.py) provides an isolated SQLite database.
    """
    holder = Captured()

    # Real collectors, fake network.
    monkeypatch.setattr(
        collectors_base.requests,
        "get",
        lambda url, **kwargs: _FakeHTTPResponse(_route(url)),
    )

    # Real evaluator logic, fake Gemini transport.
    monkeypatch.setattr(evaluator, "_client", lambda: _FakeGeminiClient(holder))
    monkeypatch.setattr(evaluator.time, "sleep", lambda *_: None)

    # Real notifiers, fake Slack + SMTP transports.
    monkeypatch.setattr(settings, "slack_webhook", "https://hooks/integration")
    monkeypatch.setattr(
        slack_mod.requests,
        "post",
        lambda url, json, timeout: holder.slack.append(json["text"])
        or _FakeHTTPResponse(""),
    )

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_user", "user@example.com")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "email_recipient", "to@example.com")
    monkeypatch.setattr(
        email_mod.smtplib,
        "SMTP_SSL",
        lambda host, port: _FakeSMTP(holder, host, port),
    )

    monkeypatch.setattr(settings, "min_score", 80)

    return holder
