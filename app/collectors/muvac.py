"""Collector for Muvac orchestra auditions (https://www.muvac.com)."""
from __future__ import annotations

from typing import Any

from app.collectors.base import BaseCollector
from app.models import Opportunity

# muvac.com is a JavaScript single-page app: the HTML served to plain HTTP
# clients contains no listings at all, which is why scraping it returned an
# empty result. The public "browse" page loads its data from this JSON API
# instead, so we query it directly.
API_URL = "https://api.muvac.com/browse/opportunities/vacancy"

# Public detail pages follow /en/vacancy/<customSlug>.
DETAIL_URL = "https://www.muvac.com/en/vacancy/{slug}"

# The API returns 404 unless a muvac.com Referer is present.
API_HEADERS = {"Referer": "https://www.muvac.com/", "Accept": "application/json"}

# The agent tracks violin positions only (see Musical Chairs' /violin/jobs).
# Muvac tags each opportunity with an expertise "group" such as
# "instruments.violin"; we keep only those.
INSTRUMENT_GROUP = "instruments.violin"


class MuvacCollector(BaseCollector):
    """Collect audition listings from the Muvac public browse API."""

    source = "muvac"

    def collect(self) -> list[Opportunity]:
        payload = self.fetch_json(API_URL, headers=API_HEADERS)
        items = ((payload.get("data") or {}).get("items")) or []

        opportunities: list[Opportunity] = []
        for item in items:
            slug = item.get("customSlug") or item.get("slug")
            title = self.clean_text(item.get("title") or "")
            if not slug or not title:
                continue
            if not self._matches_instrument(item.get("expertises") or []):
                continue

            profile = item.get("profile") or {}
            opportunities.append(
                Opportunity(
                    source=self.source,
                    title=title,
                    organization=self.clean_text(profile.get("name") or ""),
                    url=DETAIL_URL.format(slug=slug),
                    content=self._describe(item, profile),
                )
            )

        return self._dedupe(opportunities)

    @staticmethod
    def _matches_instrument(expertises: list[dict[str, Any]]) -> bool:
        return any(e.get("group") == INSTRUMENT_GROUP for e in expertises)

    def _describe(self, item: dict[str, Any], profile: dict[str, Any]) -> str:
        """Build a short human-readable description for the evaluator."""
        parts: list[str] = [self.clean_text(item.get("title") or "")]

        organization = self.clean_text(profile.get("name") or "")
        if organization:
            parts.append(organization)

        location = " ".join(
            p
            for p in (
                self.clean_text(profile.get("city") or ""),
                (profile.get("countryCode") or "").upper(),
            )
            if p
        )
        if location:
            parts.append(location)

        instruments = self._instruments(item.get("expertises") or [])
        if instruments:
            parts.append(instruments)

        sub_type = self.clean_text(item.get("subType") or "")
        if sub_type:
            parts.append(sub_type)

        return " | ".join(parts)

    @staticmethod
    def _instruments(expertises: list[dict[str, Any]]) -> str:
        """Flatten the expertise/group/instrument metadata into a string."""
        values: list[str] = []
        for expertise in expertises:
            for key in ("group", "expertise"):
                value = expertise.get(key)
                if value:
                    values.append(str(value).split(".")[-1].replace("-", " "))
            for instrument in expertise.get("instruments") or []:
                if instrument:
                    values.append(str(instrument))
        return ", ".join(dict.fromkeys(values))

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
