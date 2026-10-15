"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the orchestra opportunity agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Which backend evaluate() uses: "gemini" or "groq".
    eval_provider: str = "gemini"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    # Comma-separated fallback models tried in order if the primary model is
    # unavailable (e.g. 503 overloaded / 404 not found for this key).
    gemini_fallback_models: str = "gemini-2.5-flash,gemini-2.0-flash"
    # Minimum seconds between Gemini requests, to stay under free-tier
    # requests-per-minute quotas and avoid 429 storms. Set to 0 to disable.
    gemini_min_interval_seconds: float = 6.5

    # Groq (https://console.groq.com) - free, higher-rate-limit alternative.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fallback_models: str = "llama-3.1-8b-instant"
    groq_min_interval_seconds: float = 0.0

    # Database
    database_url: str = "sqlite:///opportunities.db"

    # API access; required for GraphQL requests.
    api_token: str = ""

    # Notifications
    min_score: int = 80
    # Slack Incoming Webhook URL (cílový kanál je dán při vytvoření webhooku).
    slack_webhook: str = ""

    # Email (SMTP over SSL)
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    email_recipient: str = ""


settings = Settings()
