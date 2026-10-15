"""Weekly AI report generation over stored opportunities."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

from app.geo import distance_from_prague_km
from app.storage.database import OpportunityEntity, SessionLocal

# Distance used for sorting when a city is unknown, so such items sort last.
_UNKNOWN_DISTANCE_KM = float("inf")


def _recent_opportunities(days: int = 7) -> list[OpportunityEntity]:
    since = datetime.now(UTC) - timedelta(days=days)
    with SessionLocal() as session:
        items = (
            session.query(OpportunityEntity)
            .filter(OpportunityEntity.created_at >= since)
            .all()
        )

    def sort_key(item: OpportunityEntity) -> tuple[float, int]:
        distance = distance_from_prague_km(item.city or "")
        return (
            _UNKNOWN_DISTANCE_KM if distance is None else distance,
            -(item.score or 0),
        )

    return sorted(items, key=sort_key)


def build_weekly_report(days: int = 7) -> str:
    """Build a plain-text weekly summary of collected opportunities.

    Sorted by proximity to Prague first, then by relevance score.
    """
    items = _recent_opportunities(days)
    if not items:
        return "Za poslední týden nebyly nalezeny žádné nové konkurzy."

    lines = [f"Týdenní přehled konkurzů (posledních {days} dní):", ""]
    for item in items:
        lines.append(
            f"[{item.score}] {item.position or item.title} – "
            f"{item.orchestra or item.organization}"
        )
        if item.city or item.country:
            distance = distance_from_prague_km(item.city or "")
            place = f"Místo: {item.city} {item.country}".rstrip()
            if distance is not None:
                place += f" ({distance:.0f} km od Prahy)"
            lines.append(f"    {place}")
        if item.deadline:
            lines.append(f"    Deadline: {item.deadline}")
        lines.append(f"    {item.url}")
        if item.summary:
            lines.append(f"    {item.summary}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    days_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(build_weekly_report(days=days_arg))
