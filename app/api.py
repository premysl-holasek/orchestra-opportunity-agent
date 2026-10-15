"""FastAPI application exposing read-only GraphQL queries."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from hmac import compare_digest

import strawberry
from fastapi import Depends, FastAPI, Header, HTTPException
from strawberry.fastapi import GraphQLRouter

from app.agents.weekly_report import build_weekly_report
from app.services import get_opportunity, search_opportunities
from app.storage.database import OpportunityEntity, init_db
from config import settings


@strawberry.type
@dataclass
class OpportunityType:
    id: int
    url: str
    source: str | None
    title: str | None
    organization: str | None
    position: str | None
    orchestra: str | None
    city: str | None
    country: str | None
    deadline: str | None
    score: int | None
    summary: str | None
    created_at: datetime | None


@strawberry.type
@dataclass
class OpportunityPageType:
    items: list[OpportunityType]
    total: int
    limit: int
    offset: int


def _to_graphql(item: OpportunityEntity) -> OpportunityType:
    return OpportunityType(
        id=item.id,
        url=item.url,
        source=item.source,
        title=item.title,
        organization=item.organization,
        position=item.position,
        orchestra=item.orchestra,
        city=item.city,
        country=item.country,
        deadline=item.deadline,
        score=item.score,
        summary=item.summary,
        created_at=item.created_at,
    )


@strawberry.type
class Query:
    @strawberry.field
    async def opportunities(
        self,
        limit: int = 25,
        offset: int = 0,
        min_score: int | None = None,
        source: str | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> OpportunityPageType:
        page = await asyncio.to_thread(
            search_opportunities,
            limit=limit,
            offset=offset,
            min_score=min_score,
            source=source,
            country=country,
            query=search,
        )
        return OpportunityPageType(
            items=[_to_graphql(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @strawberry.field
    async def opportunity(self, id: int) -> OpportunityType | None:
        item = await asyncio.to_thread(get_opportunity, id)
        return None if item is None else _to_graphql(item)

    @strawberry.field
    async def weekly_report(self, days: int = 7) -> str:
        if not 1 <= days <= 365:
            raise ValueError("days must be between 1 and 365")
        return await asyncio.to_thread(build_weekly_report, days)


schema = strawberry.Schema(query=Query)


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Fail closed until a server-side API token has been configured."""
    if not settings.api_token:
        raise HTTPException(status_code=503, detail="GraphQL API is not configured")

    scheme, separator, token = (authorization or "").partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not compare_digest(token, settings.api_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await asyncio.to_thread(init_db)
    yield


app = FastAPI(title="Orchestra Opportunity API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(
    GraphQLRouter(schema),
    prefix="/graphql",
    dependencies=[Depends(require_api_token)],
)