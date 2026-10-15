"""Tests for application configuration defaults."""
from __future__ import annotations

from config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.gemini_model == "gemini-flash-latest"
    assert s.gemini_min_interval_seconds == 6.5
    assert s.eval_provider == "gemini"
    assert s.groq_model == "llama-3.3-70b-versatile"
    assert s.database_url == "sqlite:///opportunities.db"
    assert s.min_score == 80
    assert s.smtp_port == 465
    assert s.gemini_api_key == ""
    assert s.slack_webhook == ""


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abc")
    monkeypatch.setenv("MIN_SCORE", "50")
    s = Settings(_env_file=None)
    assert s.gemini_api_key == "abc"
    assert s.min_score == 50
