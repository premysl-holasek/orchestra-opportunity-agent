"""Collector for Czech violin-teaching vacancies (conservatories, ZUŠ, HAMU/JAMU)."""
from __future__ import annotations

from app.collectors.base import BaseCollector
from app.models import Opportunity

# Manually curated list of Czech institutions that employ violin teachers:
# conservatories, music universities and job portals aggregating ZUŠ vacancies.
# Add or adjust entries as needed. Prefer a "volná místa" / careers page when
# the institution has one; otherwise the homepage is used as a best-effort URL.
CZECH_TEACHING_SOURCES: list[dict[str, str]] = [
    # --- Konzervatoře (hlavní zaměstnavatelé učitelů houslí) ---
    {
        "organization": "Pražská konzervatoř",
        "url": "https://prazskakonzervator.cz/uredni-deska/#volna-mista",
    },
    {
        "organization": "Konzervatoř Brno",
        "url": "https://konzervatorbrno.eu/?page_id=1903",
    },
    {
        "organization": "Janáčkova konzervatoř Ostrava",
        "url": "https://www.jko.cz",
    },
    {
        "organization": "Konzervatoř Plzeň",
        "url": "https://www.konzervatorplzen.cz",
    },
    {
        "organization": "Konzervatoř Pardubice",
        "url": "https://www.konzervatorpardubice.eu/o-%C5%A1kole/%C3%BA%C5%99edn%C3%AD-deska",
    },
    {
        "organization": "Konzervatoř České Budějovice",
        "url": "https://www.konzervatorcb.cz",
    },
    {
        "organization": "Konzervatoř P. J. Vejvanovského Kroměříž",
        "url": "https://www.konzkm.cz",
    },
    {
        "organization": "Konzervatoř Teplice",
        "url": "https://www.konzervatorteplice.cz/skola/volna-mista",
    },
    # --- Vysoké školy ---
    {
        "organization": "HAMU (AMU Praha)",
        "url": "https://www.hamu.cz/cs/uredni-deska/volna-mista-konkurzy/",
    },
    {
        "organization": "JAMU Brno",
        "url": "https://www.jamu.cz/jamu/o-jamu/volna-mista/",
    },
    # --- Portály agregující nabídky ZUŠ ---
    {
        "organization": "jobs.cz (učitel houslí)",
        "url": "https://www.jobs.cz/prace/?q%5B%5D=u%C4%8Ditel+houslI",
    },
    {
        "organization": "prace.cz (učitel houslí)",
        "url": "https://www.prace.cz/hledat/?q=u%C4%8Ditel+houslI",
    },
]


class CzechTeachingCollector(BaseCollector):
    """Fetch each curated page and emit it as a single opportunity.

    Each page becomes one opportunity whose ``content`` is the page text.
    The evaluator then decides relevance and extracts structured fields.
    """

    source = "czech_teaching"

    def collect(self) -> list[Opportunity]:
        opportunities: list[Opportunity] = []

        for entry in CZECH_TEACHING_SOURCES:
            url = entry["url"]
            organization = entry["organization"]

            try:
                soup = self.fetch(url)
            except Exception:  # noqa: BLE001 - skip a single broken page
                continue

            title_tag = soup.find("title")
            title = (
                self.clean_text(title_tag.get_text())
                if title_tag
                else organization
            )

            body = soup.find("body")
            content = self.clean_text(body.get_text()) if body else ""
            # Keep the prompt small; trim very long pages.
            content = content[:8000]

            opportunities.append(
                Opportunity(
                    source=self.source,
                    title=title,
                    organization=organization,
                    url=url,
                    content=content or title,
                )
            )

        return opportunities
