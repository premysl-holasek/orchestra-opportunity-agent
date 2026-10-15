"""Shared read operations for API and agent-facing adapters."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_

from app.storage import database

OpportunityEntity = database.OpportunityEntity


@dataclass(frozen=True)
class OpportunityPage:
    items: list[OpportunityEntity]
    total: int
    limit: int
    offset: int


def search_opportunities(
    *,
    limit: int = 25,
    offset: int = 0,
    min_score: int | None = None,
    source: str | None = None,
    country: str | None = None,
    query: str | None = None,
) -> OpportunityPage:
    """Search stored opportunities with stable ordering and bounded paging."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if min_score is not None and not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")

    with database.SessionLocal() as session:
        statement = session.query(OpportunityEntity)
        if min_score is not None:
            statement = statement.filter(OpportunityEntity.score >= min_score)
        if source:
            statement = statement.filter(OpportunityEntity.source == source)
        if country:
            statement = statement.filter(OpportunityEntity.country == country)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.filter(
                or_(
                    OpportunityEntity.title.ilike(pattern),
                    OpportunityEntity.organization.ilike(pattern),
                    OpportunityEntity.position.ilike(pattern),
                    OpportunityEntity.orchestra.ilike(pattern),
                    OpportunityEntity.city.ilike(pattern),
                )
            )

        total = statement.count()
        items = (
            statement.order_by(
                func.coalesce(OpportunityEntity.score, 0).desc(),
                OpportunityEntity.created_at.desc(),
                OpportunityEntity.id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    return OpportunityPage(items=items, total=total, limit=limit, offset=offset)


def get_opportunity(opportunity_id: int) -> OpportunityEntity | None:
    """Return one stored opportunity by its database ID."""
    with database.SessionLocal() as session:
        return session.get(OpportunityEntity, opportunity_id)