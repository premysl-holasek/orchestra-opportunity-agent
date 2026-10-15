"""Tests for the SMTP email notifier."""
from __future__ import annotations

import smtplib

from app.notifications import email
from config import settings


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_user", "user@example.com")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "email_recipient", "to@example.com")


class _FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logged_in = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent = msg


def test_send_email_skips_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    assert email.send_email("subj", "body") is False


def test_send_email_sends_message(monkeypatch):
    _configure(monkeypatch)
    _FakeSMTP.instances.clear()
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", _FakeSMTP)

    assert email.send_email("My subject", "Body text") is True

    inst = _FakeSMTP.instances[-1]
    assert inst.host == "smtp.example.com"
    assert inst.logged_in == ("user@example.com", "secret")
    assert inst.sent["Subject"] == "My subject"
    assert inst.sent["To"] == "to@example.com"
    assert inst.sent.get_content().strip() == "Body text"


def test_send_email_returns_false_on_smtp_error(monkeypatch):
    _configure(monkeypatch)

    def _raise(*a, **k):
        raise smtplib.SMTPException("nope")

    monkeypatch.setattr(email.smtplib, "SMTP_SSL", _raise)
    assert email.send_email("s", "b") is False
