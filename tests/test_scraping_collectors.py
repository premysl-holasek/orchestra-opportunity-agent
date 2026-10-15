"""Tests for the Musical Chairs and Muvac scraping collectors."""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.collectors.musicalchairs import MusicalChairsCollector
from app.collectors.muvac import MuvacCollector


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_musicalchairs_collect_extracts_jobs(monkeypatch):
    html = """
    <html><body>
      <a href="/violin/jobs/123">First Violin – Prague</a>
      <a href="/violin/jobs/456">  Tutti Violin  </a>
      <a href="/about">About</a>
    </body></html>
    """
    collector = MusicalChairsCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))

    result = collector.collect()

    assert len(result) == 2
    assert result[0].source == "musicalchairs"
    assert result[0].title == "First Violin – Prague"
    assert result[0].url.endswith("/violin/jobs/123")
    # whitespace collapsed
    assert result[1].title == "Tutti Violin"


def test_musicalchairs_skips_empty_titles(monkeypatch):
    html = '<a href="/jobs/1"></a>'
    collector = MusicalChairsCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))
    assert collector.collect() == []


def test_musicalchairs_dedupes_urls(monkeypatch):
    html = """
    <a href="/jobs/1">One</a>
    <a href="/jobs/1">One again</a>
    """
    collector = MusicalChairsCollector()
    monkeypatch.setattr(collector, "fetch", lambda url: _soup(html))
    result = collector.collect()
    assert len(result) == 1


def test_muvac_collect_extracts_jobs(monkeypatch):
    payload = {
        "error": False,
        "data": {
            "items": [
                {
                    "title": "Principal Violin",
                    "customSlug": "berlin-phil-abc123",
                    "slug": "berlin-phil-abc123",
                    "subType": "permanent",
                    "expertises": [
                        {
                            "expertise": "expertise.instrumentalist",
                            "group": "instruments.violin",
                            "instruments": [],
                        }
                    ],
                    "profile": {
                        "name": "Berlin Philharmonic",
                        "city": "Berlin",
                        "countryCode": "de",
                    },
                },
                {
                    "title": "  Concertmaster  ",
                    "customSlug": "vienna-xyz789",
                    "expertises": [{"group": "instruments.violin"}],
                    "profile": {
                        "name": "Vienna Phil",
                        "city": "Vienna",
                        "countryCode": "at",
                    },
                },
                {
                    "title": "Solo Cello",
                    "customSlug": "cello-999",
                    "expertises": [{"group": "instruments.cello"}],
                    "profile": {"name": "Some Orchestra"},
                },
                {"title": "No slug should be skipped", "profile": {}},
            ]
        },
    }
    collector = MuvacCollector()
    monkeypatch.setattr(collector, "fetch_json", lambda url, headers=None: payload)

    result = collector.collect()

    urls = {o.url for o in result}
    titles = {o.title for o in result}
    assert len(result) == 2
    assert any(u.endswith("/en/vacancy/berlin-phil-abc123") for u in urls)
    # whitespace collapsed
    assert "Concertmaster" in titles
    # non-violin positions are filtered out
    assert "Solo Cello" not in titles
    assert all(o.source == "muvac" for o in result)
    # organization and context are captured for the evaluator
    principal = next(o for o in result if o.title == "Principal Violin")
    assert principal.organization == "Berlin Philharmonic"
    assert "Berlin" in principal.content
    assert "violin" in principal.content.lower()


def test_muvac_dedupes_urls(monkeypatch):
    violin = [{"group": "instruments.violin"}]
    payload = {
        "data": {
            "items": [
                {
                    "title": "A",
                    "customSlug": "dup-slug",
                    "expertises": violin,
                    "profile": {},
                },
                {
                    "title": "A dup",
                    "customSlug": "dup-slug",
                    "expertises": violin,
                    "profile": {},
                },
                {
                    "title": "B",
                    "customSlug": "other-slug",
                    "expertises": violin,
                    "profile": {},
                },
            ]
        }
    }
    collector = MuvacCollector()
    monkeypatch.setattr(collector, "fetch_json", lambda url, headers=None: payload)
    result = collector.collect()
    assert len(result) == 2


def test_muvac_keeps_only_violin(monkeypatch):
    payload = {
        "data": {
            "items": [
                {
                    "title": "Tutti Violin",
                    "customSlug": "v1",
                    "expertises": [{"group": "instruments.violin"}],
                    "profile": {},
                },
                {
                    "title": "Principal Horn",
                    "customSlug": "h1",
                    "expertises": [{"group": "instruments.horn"}],
                    "profile": {},
                },
                {"title": "Untagged", "customSlug": "u1", "profile": {}},
            ]
        }
    }
    collector = MuvacCollector()
    monkeypatch.setattr(collector, "fetch_json", lambda url, headers=None: payload)
    result = collector.collect()
    assert [o.title for o in result] == ["Tutti Violin"]


def test_muvac_handles_empty_payload(monkeypatch):
    collector = MuvacCollector()
    monkeypatch.setattr(collector, "fetch_json", lambda url, headers=None: {})
    assert collector.collect() == []
