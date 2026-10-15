"""Tests for the Gemini-backed evaluator agent."""
from __future__ import annotations

import json

import httpx
import pytest
from google.genai import errors as genai_errors
from groq import APIStatusError as GroqAPIStatusError

from app.agents import evaluator
from app.models import Evaluation, Opportunity
from config import settings


@pytest.fixture
def opportunity() -> Opportunity:
    return Opportunity(
        source="muvac",
        title="First Violin",
        organization="Czech Philharmonic",
        url="https://e/1",
        content="Audition for first violin.",
    )


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, behaviors):
        # behaviors: list of either a string (-> response.text) or an Exception
        self._behaviors = list(behaviors)
        self.calls = 0

    def generate_content(self, *, model, contents, config):
        self.calls += 1
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return _FakeResponse(behavior)


class _FakeClient:
    def __init__(self, behaviors):
        self.models = _FakeModels(behaviors)


def _api_error(code: int) -> genai_errors.APIError:
    return genai_errors.APIError(
        code, {"error": {"message": "x", "status": "UNAVAILABLE"}}
    )


def _groq_error(status_code: int) -> GroqAPIStatusError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/x")
    response = httpx.Response(status_code, request=request)
    return GroqAPIStatusError("boom", response=response, body=None)


class _FakeGroqMessage:
    def __init__(self, content):
        self.content = content


class _FakeGroqChoice:
    def __init__(self, content):
        self.message = _FakeGroqMessage(content)


class _FakeGroqResponse:
    def __init__(self, content):
        self.choices = [_FakeGroqChoice(content)]


class _FakeGroqCompletions:
    def __init__(self, behaviors):
        self._behaviors = list(behaviors)
        self.calls = 0

    def create(self, *, model, messages, response_format):
        self.calls += 1
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return _FakeGroqResponse(behavior)


class _FakeGroqChat:
    def __init__(self, behaviors):
        self.completions = _FakeGroqCompletions(behaviors)


class _FakeGroqClient:
    def __init__(self, behaviors):
        self.chat = _FakeGroqChat(behaviors)


# --- _parse_json -----------------------------------------------------------

def test_parse_json_plain():
    assert evaluator._parse_json('{"score": 5}') == {"score": 5}


def test_parse_json_code_fence():
    text = '```json\n{"score": 7}\n```'
    assert evaluator._parse_json(text) == {"score": 7}


def test_parse_json_with_surrounding_text():
    text = 'Here you go: {"score": 9} thanks'
    assert evaluator._parse_json(text) == {"score": 9}


def test_parse_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        evaluator._parse_json("not json at all")


# --- evaluate --------------------------------------------------------------

def _patch_client(monkeypatch, behaviors, fallback_models=""):
    # Default to a single-model chain so call counts are deterministic; tests
    # that exercise fallback set fallback_models explicitly.
    monkeypatch.setattr(settings, "gemini_fallback_models", fallback_models)
    client = _FakeClient(behaviors)
    monkeypatch.setattr(evaluator, "_client", lambda: client)
    monkeypatch.setattr(evaluator.time, "sleep", lambda *_: None)
    return client


def test_evaluate_success(monkeypatch, opportunity):
    payload = json.dumps(
        {
            "position": "First Violin",
            "orchestra": "Czech Philharmonic",
            "city": "Prague",
            "country": "CZ",
            "deadline": "2026-09-01",
            "score": 85,
            "summary": "Konkurz.",
        }
    )
    _patch_client(monkeypatch, [payload])

    result = evaluator.evaluate(opportunity)
    assert isinstance(result, Evaluation)
    assert result.position == "First Violin"
    assert result.score == 85
    assert result.city == "Prague"


def test_evaluate_retries_then_succeeds(monkeypatch, opportunity):
    payload = json.dumps({"score": 70})
    client = _patch_client(monkeypatch, [_api_error(503), payload])

    result = evaluator.evaluate(opportunity)
    assert result.score == 70
    assert client.models.calls == 2


def test_evaluate_exhausts_retries_returns_empty(monkeypatch, opportunity):
    behaviors = [_api_error(503)] * evaluator.MAX_RETRIES
    client = _patch_client(monkeypatch, behaviors)

    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()
    assert client.models.calls == evaluator.MAX_RETRIES


def test_evaluate_non_retryable_error_returns_empty(monkeypatch, opportunity):
    client = _patch_client(monkeypatch, [_api_error(400)])

    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()
    # Non-retryable: only one attempt.
    assert client.models.calls == 1


def test_evaluate_unparseable_output_returns_empty(monkeypatch, opportunity):
    _patch_client(monkeypatch, ["this is not json"])
    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()


def test_evaluate_handles_empty_text(monkeypatch, opportunity):
    _patch_client(monkeypatch, [None])
    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()


# --- model fallback chain --------------------------------------------------

def test_model_chain_includes_primary_then_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "gemini_model", "primary")
    monkeypatch.setattr(settings, "gemini_fallback_models", "fb1, fb2")
    assert evaluator._model_chain() == ["primary", "fb1", "fb2"]


def test_model_chain_dedupes_and_ignores_blanks(monkeypatch):
    monkeypatch.setattr(settings, "gemini_model", "primary")
    monkeypatch.setattr(settings, "gemini_fallback_models", "primary, , fb1")
    assert evaluator._model_chain() == ["primary", "fb1"]


def test_evaluate_falls_back_to_next_model_on_overload(monkeypatch, opportunity):
    payload = json.dumps({"score": 95})
    # Primary exhausts its retries with 503, fallback model then succeeds.
    behaviors = [_api_error(503)] * evaluator.MAX_RETRIES + [payload]
    client = _patch_client(monkeypatch, behaviors, fallback_models="fallback-1")

    result = evaluator.evaluate(opportunity)
    assert result.score == 95
    # MAX_RETRIES calls on the primary + 1 successful call on the fallback.
    assert client.models.calls == evaluator.MAX_RETRIES + 1


def test_evaluate_falls_back_on_model_not_found(monkeypatch, opportunity):
    payload = json.dumps({"score": 80})
    # Primary returns 404 (not retried), fallback succeeds immediately.
    client = _patch_client(
        monkeypatch, [_api_error(404), payload], fallback_models="fallback-1"
    )

    result = evaluator.evaluate(opportunity)
    assert result.score == 80
    assert client.models.calls == 2


def test_evaluate_returns_empty_when_all_models_fail(monkeypatch, opportunity):
    behaviors = [_api_error(503)] * (evaluator.MAX_RETRIES * 2)
    client = _patch_client(monkeypatch, behaviors, fallback_models="fallback-1")

    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()
    # Both models exhausted their retries.
    assert client.models.calls == evaluator.MAX_RETRIES * 2


# --- Groq provider -----------------------------------------------------------

def _patch_groq_client(monkeypatch, behaviors, fallback_models=""):
    monkeypatch.setattr(settings, "eval_provider", "groq")
    monkeypatch.setattr(settings, "groq_fallback_models", fallback_models)
    client = _FakeGroqClient(behaviors)
    monkeypatch.setattr(evaluator, "_groq_client", lambda: client)
    monkeypatch.setattr(evaluator.time, "sleep", lambda *_: None)
    return client


def test_evaluate_uses_groq_when_selected(monkeypatch, opportunity):
    payload = json.dumps({"score": 85, "position": "First Violin"})
    _patch_groq_client(monkeypatch, [payload])

    result = evaluator.evaluate(opportunity)
    assert result.score == 85
    assert result.position == "First Violin"


def test_evaluate_groq_retries_then_succeeds(monkeypatch, opportunity):
    payload = json.dumps({"score": 70})
    client = _patch_groq_client(monkeypatch, [_groq_error(429), payload])

    result = evaluator.evaluate(opportunity)
    assert result.score == 70
    assert client.chat.completions.calls == 2


def test_evaluate_groq_falls_back_to_next_model(monkeypatch, opportunity):
    payload = json.dumps({"score": 95})
    behaviors = [_groq_error(429)] * evaluator.MAX_RETRIES + [payload]
    client = _patch_groq_client(monkeypatch, behaviors, fallback_models="fallback-1")

    result = evaluator.evaluate(opportunity)
    assert result.score == 95
    assert client.chat.completions.calls == evaluator.MAX_RETRIES + 1


def test_evaluate_groq_returns_empty_when_all_models_fail(monkeypatch, opportunity):
    behaviors = [_groq_error(429)] * (evaluator.MAX_RETRIES * 2)
    client = _patch_groq_client(monkeypatch, behaviors, fallback_models="fallback-1")

    result = evaluator.evaluate(opportunity)
    assert result == Evaluation()
    assert client.chat.completions.calls == evaluator.MAX_RETRIES * 2


def test_groq_model_chain_includes_primary_then_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "groq_model", "primary")
    monkeypatch.setattr(settings, "groq_fallback_models", "fb1, fb2")
    assert evaluator._groq_model_chain() == ["primary", "fb1", "fb2"]
