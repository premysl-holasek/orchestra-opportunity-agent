"""Tests for the collector base class and HTTP helpers."""
from __future__ import annotations

import pytest
import requests
from bs4 import BeautifulSoup

from app.collectors import base
from app.collectors.base import BaseCollector
from app.models import Opportunity


class _Raising(BaseCollector):
    source = "raising"

    def collect(self):
        raise RuntimeError("boom")


class _Working(BaseCollector):
    source = "working"

    def collect(self):
        return [
            Opportunity(
                source=self.source,
                title="t",
                organization="o",
                url="https://e/1",
                content="c",
            )
        ]


def test_safe_collect_swallows_exceptions():
    assert _Raising().safe_collect() == []


def test_safe_collect_returns_collected_items():
    result = _Working().safe_collect()
    assert len(result) == 1
    assert result[0].source == "working"


def test_clean_text_collapses_whitespace():
    assert BaseCollector.clean_text("  a\n\t b   c ") == "a b c"


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_fetch_returns_soup(monkeypatch):
    html = "<html><body><h1>Hi</h1></body></html>"
    monkeypatch.setattr(
        base.requests, "get", lambda *a, **k: _FakeResponse(html)
    )
    soup = BaseCollector.fetch("https://example.com")
    assert isinstance(soup, BeautifulSoup)
    assert soup.find("h1").get_text() == "Hi"


def test_fetch_raises_on_http_error(monkeypatch):
    class _Bad(_FakeResponse):
        def raise_for_status(self):
            raise requests.HTTPError("500")

    monkeypatch.setattr(
        base.requests, "get", lambda *a, **k: _Bad("oops")
    )
    with pytest.raises(requests.HTTPError):
        BaseCollector.fetch("https://example.com")
