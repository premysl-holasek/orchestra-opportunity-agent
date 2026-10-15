"""Tests for the curated Czech orchestras collector."""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.collectors import czech_orchestras
from app.collectors.czech_orchestras import CzechOrchestrasCollector


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_collect_builds_one_opportunity_per_page(monkeypatch):
    monkeypatch.setattr(
        czech_orchestras,
        "CZECH_ORCHESTRAS",
        [{"organization": "Test Phil", "url": "https://test/aud"}],
    )
    html = "<html><head><title>Auditions</title></head><body>Hello world</body></html>"
    collector = CzechOrchestrasCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()

    assert len(result) == 1
    opp = result[0]
    assert opp.source == "czech_orchestras"
    assert opp.organization == "Test Phil"
    assert opp.title == "Auditions"
    assert "Hello world" in opp.content
    assert opp.url == "https://test/aud"


def test_collect_falls_back_to_organization_without_title(monkeypatch):
    monkeypatch.setattr(
        czech_orchestras,
        "CZECH_ORCHESTRAS",
        [{"organization": "No Title Phil", "url": "https://test/aud"}],
    )
    html = "<html><body>Body only</body></html>"
    collector = CzechOrchestrasCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()
    assert result[0].title == "No Title Phil"


def test_collect_skips_pages_that_fail(monkeypatch):
    monkeypatch.setattr(
        czech_orchestras,
        "CZECH_ORCHESTRAS",
        [
            {"organization": "Good", "url": "https://good"},
            {"organization": "Bad", "url": "https://bad"},
        ],
    )

    def fake_fetch(url):
        if url == "https://bad":
            raise RuntimeError("down")
        return _soup("<html><title>OK</title><body>x</body></html>")

    collector = CzechOrchestrasCollector()
    monkeypatch.setattr(collector, "fetch", fake_fetch)

    result = collector.collect()
    assert len(result) == 1
    assert result[0].organization == "Good"


def test_collect_trims_long_content(monkeypatch):
    monkeypatch.setattr(
        czech_orchestras,
        "CZECH_ORCHESTRAS",
        [{"organization": "Big", "url": "https://big"}],
    )
    body = "a " * 10000  # > 8000 chars after join
    html = f"<html><title>T</title><body>{body}</body></html>"
    collector = CzechOrchestrasCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()
    assert len(result[0].content) <= 8000
