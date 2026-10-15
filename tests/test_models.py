"""Tests for the shared Pydantic models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import Evaluation, Opportunity


def test_opportunity_requires_all_fields():
    with pytest.raises(ValidationError):
        Opportunity(source="muvac", title="x")  # missing fields


def test_opportunity_roundtrip():
    opp = Opportunity(
        source="muvac",
        title="t",
        organization="o",
        url="https://e/1",
        content="c",
    )
    assert opp.model_dump() == {
        "source": "muvac",
        "title": "t",
        "organization": "o",
        "url": "https://e/1",
        "content": "c",
    }


def test_evaluation_defaults_are_empty():
    ev = Evaluation()
    assert ev.position == ""
    assert ev.orchestra == ""
    assert ev.city == ""
    assert ev.country == ""
    assert ev.deadline == ""
    assert ev.score == 0
    assert ev.summary == ""


def test_evaluation_score_coerced_to_int():
    ev = Evaluation(score="80")
    assert ev.score == 80
