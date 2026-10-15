"""Collector for a manually maintained list of Czech orchestra career pages."""
from __future__ import annotations

from urllib.parse import urljoin

from app.collectors.base import BaseCollector
from app.models import Opportunity

# Manually curated list of Czech orchestras and their audition/career pages.
# Add or adjust entries as needed.
CZECH_ORCHESTRAS: list[dict[str, str]] = [
    {
        "organization": "Czech Philharmonic",
        "url": "https://www.ceskafilharmonie.cz/en/orchestra/auditions/",
    },
    {
        "organization": "Filharmonie Brno",
        "url": "https://www.filharmonie-brno.cz/en/orchestra/auditions/",
    },
    {
        "organization": "Prague Symphony Orchestra FOK",
        "url": "https://www.fok.cz/en/auditions",
    },
    {
        "organization": "Janáček Philharmonic Ostrava",
        "url": "https://www.jfo.cz/en/auditions",
    },
    {
        "organization": "PKF - Prague Philharmonia",
        "url": "https://prgphil.cz", # Často otevírají prestižní Orchestrální akademii
    },
    {
        "organization": "Prague Radio Symphony Orchestra (SOČR)",
        "url": "https://rozhlas.cz",
    },
    {
        "organization": "Czech Chamber Philharmonic Orchestra Pardubice",
        "url": "https://kfpar.cz",
    },
    {
        "organization": "South Czech Philharmonic (Jihočeská filharmonie)",
        "url": "https://jcfilharmonie.cz",
    },
    {
        "organization": "Moravian Philharmonic Olomouc",
        "url": "https://mfo.cz",
    },
    {
        "organization": "Bohuslav Martinů Philharmonic Zlín",
        "url": "https://filharmonie-zlin.cz",
    },
    {
        "organization": "North Czech Philharmonic Teplice",
        "url": "http://severoceskafilharmonie.cz",
    },
    {
        "organization": "West Bohemian Symphony Orchestra Mariánské Lázně",
        "url": "https://zso.cz",
    },
    {
        "organization": "Karlovy Vary Symphony Orchestra",
        "url": "https://kso.cz",
    },
    
    # --- Operní a divadelní orchestry (klíčoví zaměstnavatelé) ---
    {
        "organization": "National Theatre Prague (Orchestr ND / Státní opera)",
        "url": "https://narodni-divadlo.cz",
    },
    {
        "organization": "National Theatre Brno (Janáček Opera Orchestra)",
        "url": "https://ndbrno.cz",
    },
    {
        "organization": "National Moravian-Silesian Theatre Ostrava",
        "url": "https://ndm.cz",
    },
    {
        "organization": "J. K. Tyl Theatre Pilsen (DJKT)",
        "url": "https://djkt.eu",
    }
]



class CzechOrchestrasCollector(BaseCollector):
    """Fetch each curated orchestra page and emit it as a single opportunity.

    Each page becomes one opportunity whose ``content`` is the page text.
    The evaluator then decides relevance and extracts structured fields.
    """

    source = "czech_orchestras"

    def collect(self) -> list[Opportunity]:
        opportunities: list[Opportunity] = []

        for entry in CZECH_ORCHESTRAS:
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

    @staticmethod
    def _absolute(base: str, href: str) -> str:
        return urljoin(base, href)
