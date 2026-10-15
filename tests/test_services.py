"""Tests for shared opportunity query operations."""
from __future__ import annotations

import pytest

from app.models import Evaluation, Opportunity
from app.services import get_opportunity, search_opportunities
from app.storage.database import save


def _save_opportunity(url: str, *, title: str, score: int, country: str) -> int:
    opportunity = Opportunity(
        source="muvac",
        title=title,
        organization="Czech Philharmonic",
        url=url,
        content="Audition details",
    )
    evaluation = Evaluation(
        position="First Violin",
        orchestra="Czech Philharmonic",
        city="Prague",
        country=country,
        score=score,
        summary="Audition",
    )
    return save(opportunity, evaluation).id


def test_search_filters_and_orders_opportunities(db):
    _save_opportunity(
        "https://example.com/low",
        title="Violin position",
        score=70,
        country="CZ",
    )
    best_id = _save_opportunity(
        "https://example.com/high",
        title="Concertmaster audition",
        score=95,
        country="CZ",
    )
    _save_opportunity(
        "https://example.com/other-country",
        title="Concertmaster audition abroad",
        score=99,
        country="DE",
    )

    page = search_opportunities(min_score=80, country="CZ", query="concertmaster")

    assert page.total == 1
    assert page.items[0].id == best_id
    assert page.limit == 25
    assert page.offset == 0


def test_search_applies_pagination(db):
    for score in (70, 80, 90):
        _save_opportunity(
            f"https://example.com/{score}",
            title="Violin position",
            score=score,
            country="CZ",
        )

    page = search_opportunities(limit=1, offset=1)

    assert page.total == 3
    assert page.items[0].score == 80


def test_search_rejects_unbounded_pagination(db):
    with pytest.raises(ValueError, match="limit"):
        search_opportunities(limit=101)


def test_get_opportunity_returns_entity_or_none(db):
    opportunity_id = _save_opportunity(
        "https://example.com/one",
        title="Violin position",
        score=80,
        country="CZ",
    )

    assert get_opportunity(opportunity_id).url == "https://example.com/one"
    assert get_opportunity(-1) is None