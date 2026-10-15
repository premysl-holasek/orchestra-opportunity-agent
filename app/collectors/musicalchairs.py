"""Collector for Musical Chairs auditions (https://www.musicalchairs.info)."""
from __future__ import annotations

from urllib.parse import urljoin

from app.collectors.base import BaseCollector
from app.models import Opportunity

# Strings auditions listing. Change the instrument segment to track others.
LISTING_URL = "https://www.musicalchairs.info/violin/jobs"


class MusicalChairsCollector(BaseCollector):
    """Scrape audition listings from Musical Chairs.

    Selectors are best-effort and may need tuning if the site markup
    changes. Failures are swallowed by ``BaseCollector.safe_collect``.
    """

    source = "musicalchairs"

    def collect(self) -> list[Opportunity]:
        soup = self.fetch(LISTING_URL)
        opportunities: list[Opportunity] = []

        for row in soup.select("a[href*='/jobs/']"):
            href = row.get("href")
            if not isinstance(href, str) or not href:
                continue

            url = urljoin(LISTING_URL, href)
            title = self.clean_text(row.get_text())
            if not title:
                continue

            opportunities.append(
                Opportunity(
                    source=self.source,
                    title=title,
                    organization="",
                    url=url,
                    content=title,
                )
            )

        return self._dedupe(opportunities)

    @staticmethod
    def _dedupe(items: list[Opportunity]) -> list[Opportunity]:
        seen: set[str] = set()
        unique: list[Opportunity] = []
        for item in items:
            if item.url in seen:
                continue
            seen.add(item.url)
            unique.append(item)
        return unique
