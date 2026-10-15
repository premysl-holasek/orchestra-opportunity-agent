"""Base classes and helpers for opportunity collectors."""
from __future__ import annotations

import abc
import logging

import requests
from bs4 import BeautifulSoup

from app.models import Opportunity

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; OrchestraOpportunityAgent/1.0; "
        "+https://github.com/)"
    )
}

REQUEST_TIMEOUT = 30


class BaseCollector(abc.ABC):
    """Abstract collector that returns a list of opportunities."""

    #: Human-readable source identifier stored on each opportunity.
    source: str = "base"

    @abc.abstractmethod
    def collect(self) -> list[Opportunity]:
        """Fetch and return opportunities from this source."""
        raise NotImplementedError

    def safe_collect(self) -> list[Opportunity]:
        """Run ``collect`` but never raise; log and return empty on failure."""
        try:
            return self.collect()
        except Exception:  # noqa: BLE001 - collectors must not break the run
            logger.exception("Collector %s failed", self.source)
            return []

    @staticmethod
    def fetch(url: str) -> BeautifulSoup:
        """Fetch a URL and return a parsed BeautifulSoup document."""
        response = requests.get(
            url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    @staticmethod
    def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
        """Fetch a URL and return the parsed JSON payload."""
        merged = {**DEFAULT_HEADERS, **(headers or {})}
        response = requests.get(url, headers=merged, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def clean_text(text: str) -> str:
        """Collapse whitespace in extracted text."""
        return " ".join(text.split())
