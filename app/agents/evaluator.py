"""AI evaluator agent that scores and structures opportunities."""
from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from groq import APIStatusError as GroqAPIStatusError
from groq import Groq

from app.models import Evaluation, Opportunity
from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "evaluator.txt"

# Transient HTTP statuses worth retrying (overloaded / unavailable / rate limit).
RETRYABLE_STATUS = {429, 500, 503}
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0

# Timestamp (time.monotonic) of the last request made to Gemini, used to pace
# requests and stay under free-tier requests-per-minute quotas.
_last_request_at = 0.0
_last_groq_request_at = 0.0


@lru_cache(maxsize=1)
def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


@lru_cache(maxsize=1)
def _groq_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def _model_chain() -> list[str]:
    """Return the ordered list of models to try: primary then fallbacks."""
    chain = [settings.gemini_model]
    for name in settings.gemini_fallback_models.split(","):
        name = name.strip()
        if name and name not in chain:
            chain.append(name)
    return chain


def _parse_json(text: str) -> dict:
    """Parse model output into a dict, tolerating code fences/extra text."""
    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence.
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[len("json"):]
    text = text.strip()

    # Fall back to extracting the first JSON object if there is stray text.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


def _pace_request() -> None:
    """Sleep as needed to keep requests spaced out (avoids RPM 429s)."""
    global _last_request_at
    min_interval = settings.gemini_min_interval_seconds
    if min_interval > 0:
        remaining = min_interval - (time.monotonic() - _last_request_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at = time.monotonic()


def _generate_with_retry(model: str, system_prompt: str, user_content: str):
    """Call one Gemini model, retrying transient errors (503/500/429)."""
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _pace_request()
            return _client().models.generate_content(
                model=model,
                contents=user_content,
                config=config,
            )
        except genai_errors.APIError as exc:
            if exc.code not in RETRYABLE_STATUS or attempt == MAX_RETRIES:
                raise
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Gemini model %s returned %s (attempt %d/%d); retrying in %.1fs",
                model,
                exc.code,
                attempt,
                MAX_RETRIES,
                delay,
            )
            time.sleep(delay)


def _generate(system_prompt: str, user_content: str):
    """Try each model in the fallback chain until one succeeds.

    Raises the last ``APIError`` if every model fails.
    """
    last_error: genai_errors.APIError | None = None
    for model in _model_chain():
        try:
            return _generate_with_retry(model, system_prompt, user_content)
        except genai_errors.APIError as exc:
            last_error = exc
            logger.warning(
                "Gemini model %s unavailable (%s); trying next fallback",
                model,
                exc.code,
            )
    assert last_error is not None
    raise last_error


def _groq_model_chain() -> list[str]:
    """Return the ordered list of Groq models to try: primary then fallbacks."""
    chain = [settings.groq_model]
    for name in settings.groq_fallback_models.split(","):
        name = name.strip()
        if name and name not in chain:
            chain.append(name)
    return chain


def _pace_groq_request() -> None:
    """Sleep as needed to keep Groq requests spaced out."""
    global _last_groq_request_at
    min_interval = settings.groq_min_interval_seconds
    if min_interval > 0:
        remaining = min_interval - (time.monotonic() - _last_groq_request_at)
        if remaining > 0:
            time.sleep(remaining)
    _last_groq_request_at = time.monotonic()


def _groq_generate_with_retry(model: str, system_prompt: str, user_content: str):
    """Call one Groq model, retrying transient errors (503/500/429)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _pace_groq_request()
            response = _groq_client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except GroqAPIStatusError as exc:
            if exc.status_code not in RETRYABLE_STATUS or attempt == MAX_RETRIES:
                raise
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Groq model %s returned %s (attempt %d/%d); retrying in %.1fs",
                model,
                exc.status_code,
                attempt,
                MAX_RETRIES,
                delay,
            )
            time.sleep(delay)


def _groq_generate(system_prompt: str, user_content: str):
    """Try each Groq model in the fallback chain until one succeeds.

    Raises the last ``GroqAPIStatusError`` if every model fails.
    """
    last_error: GroqAPIStatusError | None = None
    for model in _groq_model_chain():
        try:
            return _groq_generate_with_retry(model, system_prompt, user_content)
        except GroqAPIStatusError as exc:
            last_error = exc
            logger.warning(
                "Groq model %s unavailable (%s); trying next fallback",
                model,
                exc.status_code,
            )
    assert last_error is not None
    raise last_error


def evaluate(opportunity: Opportunity) -> Evaluation:
    """Evaluate an opportunity and return a structured ``Evaluation``."""
    system_prompt = _load_prompt()
    user_content = (
        f"Source: {opportunity.source}\n"
        f"Title: {opportunity.title}\n"
        f"Organization: {opportunity.organization}\n"
        f"URL: {opportunity.url}\n\n"
        f"Content:\n{opportunity.content}"
    )

    try:
        if settings.eval_provider == "groq":
            raw = _groq_generate(system_prompt, user_content) or ""
        else:
            response = _generate(system_prompt, user_content)
            raw = response.text or ""
    except genai_errors.APIError as exc:
        logger.error("Gemini evaluation failed on all models: %s", exc)
        return Evaluation()
    except GroqAPIStatusError as exc:
        logger.error("Groq evaluation failed on all models: %s", exc)
        return Evaluation()

    try:
        data = _parse_json(raw)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Could not parse evaluator output: %s", raw)
        return Evaluation()

    return Evaluation(
        position=str(data.get("position", "")),
        orchestra=str(data.get("orchestra", "")),
        city=str(data.get("city", "")),
        country=str(data.get("country", "")),
        deadline=str(data.get("deadline", "")),
        score=int(data.get("score", 0) or 0),
        summary=str(data.get("summary", "")),
    )
