"""Pydantic data models shared across the application."""
from __future__ import annotations

from pydantic import BaseModel


class Opportunity(BaseModel):
    """A raw opportunity collected from a source, before evaluation."""

    source: str
    title: str
    organization: str
    url: str
    content: str


class Evaluation(BaseModel):
    """Result of the AI evaluation of an opportunity."""

    position: str = ""
    orchestra: str = ""
    city: str = ""
    country: str = ""
    deadline: str = ""
    score: int = 0
    summary: str = ""
