"""SQLite persistence layer using SQLAlchemy."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models import Evaluation, Opportunity
from config import settings


class Base(DeclarativeBase):
    pass


class OpportunityEntity(Base):
    """Database row for a stored, evaluated opportunity."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    source: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    organization: Mapped[str | None] = mapped_column(String)

    position: Mapped[str | None] = mapped_column(String)
    orchestra: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    deadline: Mapped[str | None] = mapped_column(String)

    score: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)


def init_db() -> None:
    """Create database tables if they do not exist."""
    Base.metadata.create_all(engine)


def exists(url: str) -> bool:
    """Return True if an opportunity with the given URL is already stored."""
    with SessionLocal() as session:
        return (
            session.query(OpportunityEntity)
            .filter(OpportunityEntity.url == url)
            .first()
            is not None
        )


def save(opportunity: Opportunity, evaluation: Evaluation) -> OpportunityEntity:
    """Persist an opportunity together with its evaluation."""
    entity = OpportunityEntity(
        url=opportunity.url,
        source=opportunity.source,
        title=opportunity.title,
        organization=opportunity.organization,
        position=evaluation.position,
        orchestra=evaluation.orchestra,
        city=evaluation.city,
        country=evaluation.country,
        deadline=evaluation.deadline,
        score=evaluation.score,
        summary=evaluation.summary,
    )

    with SessionLocal() as session:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    return entity
