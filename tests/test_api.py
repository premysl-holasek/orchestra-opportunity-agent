"""Tests for the authenticated GraphQL API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import app
from app.models import Evaluation, Opportunity
from app.storage.database import save
from config import settings


def test_graphql_requires_bearer_token(db, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "test-secret")

    with TestClient(app) as client:
        response = client.post(
            "/graphql", json={"query": "{ opportunities { total } }"}
        )

    assert response.status_code == 401


def test_graphql_returns_filtered_opportunities(db, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "test-secret")
    save(
        Opportunity(
            source="muvac",
            title="Concertmaster audition",
            organization="Czech Philharmonic",
            url="https://example.com/audition",
            content="Details",
        ),
        Evaluation(score=95, city="Prague", country="CZ"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/graphql",
            headers={"Authorization": "Bearer test-secret"},
            json={
                "query": """
                query {
                  opportunities(minScore: 80, country: "CZ") {
                    total
                    items { title score city }
                  }
                }
                """
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["opportunities"]["total"] == 1
    assert response.json()["data"]["opportunities"]["items"] == [
        {"title": "Concertmaster audition", "score": 95, "city": "Prague"}
    ]


def test_graphql_fails_closed_when_api_token_is_unset(db, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "")

    with TestClient(app) as client:
        response = client.post(
            "/graphql", json={"query": "{ opportunities { total } }"}
        )

    assert response.status_code == 503