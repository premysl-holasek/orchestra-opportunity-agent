"""Slack webhook notifier."""
from __future__ import annotations

import logging

import requests

from config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def send_slack(message: str) -> bool:
    """Post a message to the configured Slack Incoming Webhook.

    The target channel is fixed when the webhook is created in Slack.

    Returns True on success, False if no webhook is configured or the request
    fails.
    """
    if not settings.slack_webhook:
        logger.info("Slack webhook not configured; skipping Slack notification")
        return False

    try:
        response = requests.post(
            settings.slack_webhook,
            json={"text": message},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Failed to send Slack notification")
        return False
