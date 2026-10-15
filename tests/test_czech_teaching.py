"""Tests for the curated Czech teaching collector."""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.collectors import czech_teaching
from app.collectors.czech_teaching import CzechTeachingCollector


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_collect_builds_one_opportunity_per_page(monkeypatch):
    monkeypatch.setattr(
        czech_teaching,
        "CZECH_TEACHING_SOURCES",
        [{"organization": "Test Konzervatoř", "url": "https://test/volna-mista"}],
    )
    html = (
        "<html><head><title>Volná místa</title></head>"
        "<body>Hledáme učitele houslí</body></html>"
    )
    collector = CzechTeachingCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()

    assert len(result) == 1
    opp = result[0]
    assert opp.source == "czech_teaching"
    assert opp.organization == "Test Konzervatoř"
    assert opp.title == "Volná místa"
    assert "učitele houslí" in opp.content
    assert opp.url == "https://test/volna-mista"


def test_collect_falls_back_to_organization_without_title(monkeypatch):
    monkeypatch.setattr(
        czech_teaching,
        "CZECH_TEACHING_SOURCES",
        [{"organization": "No Title ZUŠ", "url": "https://test/jobs"}],
    )
    html = "<html><body>Body only</body></html>"
    collector = CzechTeachingCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()
    assert result[0].title == "No Title ZUŠ"


def test_collect_skips_pages_that_fail(monkeypatch):
    monkeypatch.setattr(
        czech_teaching,
        "CZECH_TEACHING_SOURCES",
        [
            {"organization": "Good", "url": "https://good"},
            {"organization": "Bad", "url": "https://bad"},
        ],
    )

    def fake_fetch(url):
        if url == "https://bad":
            raise RuntimeError("down")
        return _soup("<html><title>OK</title><body>x</body></html>")

    collector = CzechTeachingCollector()
    monkeypatch.setattr(collector, "fetch", fake_fetch)

    result = collector.collect()
    assert len(result) == 1
    assert result[0].organization == "Good"


def test_collect_trims_long_content(monkeypatch):
    monkeypatch.setattr(
        czech_teaching,
        "CZECH_TEACHING_SOURCES",
        [{"organization": "Big", "url": "https://big"}],
    )
    body = "a " * 10000  # > 8000 chars after join
    html = f"<html><title>T</title><body>{body}</body></html>"
    collector = CzechTeachingCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()
    assert len(result[0].content) <= 8000
