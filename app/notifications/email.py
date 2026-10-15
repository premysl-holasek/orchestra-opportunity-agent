"""Email notifier using SMTP over SSL."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_user
        and settings.smtp_password
        and settings.email_recipient
    )


def send_email(subject: str, body: str) -> bool:
    """Send a plain-text email via SMTP over SSL.

    Returns True on success, False if email is not configured or sending
    fails.
    """
    if not _is_configured():
        logger.info("SMTP not fully configured; skipping email notification")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.email_recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send email notification")
        return False
