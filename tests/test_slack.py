"""Tests for the Slack webhook notifier."""
from __future__ import annotations

import requests

from app.notifications import slack
from config import settings


class _Resp:
    def __init__(self, raise_exc=None):
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise self._raise


def test_send_slack_skips_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "slack_webhook", "")
    called = False

    def _post(*a, **k):
        nonlocal called
        called = True

    monkeypatch.setattr(slack.requests, "post", _post)
    assert slack.send_slack("hi") is False
    assert called is False


def test_send_slack_posts_message(monkeypatch):
    monkeypatch.setattr(settings, "slack_webhook", "https://hooks/abc")
    captured = {}

    def _post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(slack.requests, "post", _post)

    assert slack.send_slack("hello") is True
    assert captured["url"] == "https://hooks/abc"
    assert captured["json"] == {"text": "hello"}


def test_send_slack_returns_false_on_request_error(monkeypatch):
    monkeypatch.setattr(settings, "slack_webhook", "https://hooks/abc")

    def _post(*a, **k):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(slack.requests, "post", _post)
    assert slack.send_slack("hello") is False
