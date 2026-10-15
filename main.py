"""Main orchestrator: collect, evaluate, store, and notify."""
from __future__ import annotations

import logging

from app.agents.evaluator import evaluate
from app.collectors.base import BaseCollector
from app.collectors.czech_orchestras import CzechOrchestrasCollector
from app.collectors.czech_teaching import CzechTeachingCollector
from app.collectors.musicalchairs import MusicalChairsCollector
from app.collectors.muvac import MuvacCollector
from app.models import Evaluation, Opportunity
from app.notifications.email import send_email
from app.notifications.slack import send_slack
from app.storage.database import exists, init_db, save
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("orchestra")


def get_collectors() -> list[BaseCollector]:
    """Return the list of enabled collectors."""
    return [
        MuvacCollector(),
        MusicalChairsCollector(),
        CzechOrchestrasCollector(),
        CzechTeachingCollector(),
    ]


def notify(opportunity: Opportunity, evaluation: Evaluation) -> None:
    """Send notifications for a relevant opportunity."""
    subject = (
        f"[{evaluation.score}] {evaluation.position or opportunity.title} – "
        f"{evaluation.orchestra or opportunity.organization}"
    )
    body = (
        f"{evaluation.summary}\n\n"
        f"Pozice: {evaluation.position}\n"
        f"Orchestr: {evaluation.orchestra}\n"
        f"Místo: {evaluation.city} {evaluation.country}\n"
        f"Deadline: {evaluation.deadline}\n"
        f"Skóre: {evaluation.score}\n"
        f"Zdroj: {opportunity.source}\n"
        f"URL: {opportunity.url}\n"
    )

    send_slack(f"*{subject}*\n{body}")
    send_email(subject, body)


def run() -> None:
    """Run a full collection + evaluation cycle."""
    init_db()

    opportunities: list[Opportunity] = []
    for collector in get_collectors():
        found = collector.safe_collect()
        logger.info("Collector %s returned %d items", collector.source, len(found))
        opportunities.extend(found)

    processed = 0
    notified = 0
    for opportunity in opportunities:
        if exists(opportunity.url):
            continue

        evaluation = evaluate(opportunity)
        save(opportunity, evaluation)
        processed += 1

        if evaluation.score >= settings.min_score:
            notify(opportunity, evaluation)
            notified += 1

    logger.info(
        "Run complete: %d new opportunities, %d notifications sent",
        processed,
        notified,
    )


if __name__ == "__main__":
    run()
