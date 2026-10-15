"""Local MCP tools backed by the shared opportunity query service."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from app.agents.weekly_report import build_weekly_report
from app.services import get_opportunity as find_opportunity
from app.services import search_opportunities as search

mcp = FastMCP("Orchestra Opportunities")


@mcp.tool()
def search_opportunities(
    query: str | None = None,
    min_score: int | None = None,
    source: str | None = None,
    country: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> str:
    """Search evaluated orchestra and music-teaching opportunities."""
    page = search(
        query=query,
        min_score=min_score,
        source=source,
        country=country,
        limit=limit,
        offset=offset,
    )
    return json.dumps(
        {
            "items": [
                {
                    "id": item.id,
                    "url": item.url,
                    "source": item.source,
                    "title": item.title,
                    "organization": item.organization,
                    "position": item.position,
                    "orchestra": item.orchestra,
                    "city": item.city,
                    "country": item.country,
                    "deadline": item.deadline,
                    "score": item.score,
                    "summary": item.summary,
                    "created_at": item.created_at,
                }
                for item in page.items
            ],
            "total": page.total,
            "limit": page.limit,
            "offset": page.offset,
        },
        ensure_ascii=False,
        default=str,
    )


@mcp.tool()
def get_opportunity(opportunity_id: int) -> str:
    """Get one opportunity by its database ID."""
    item = find_opportunity(opportunity_id)
    if item is None:
        return "Příležitost nebyla nalezena."
    return json.dumps(
        {
            "id": item.id,
            "url": item.url,
            "source": item.source,
            "title": item.title,
            "organization": item.organization,
            "position": item.position,
            "orchestra": item.orchestra,
            "city": item.city,
            "country": item.country,
            "deadline": item.deadline,
            "score": item.score,
            "summary": item.summary,
            "created_at": item.created_at,
        },
        ensure_ascii=False,
        default=str,
    )


@mcp.tool()
def weekly_report(days: int = 7) -> str:
    """Build a text report for recent opportunities (up to one year)."""
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    return build_weekly_report(days)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()