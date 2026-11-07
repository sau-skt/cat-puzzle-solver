"""SMTP delivery with a local-log fallback when mail is not configured."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("catpuzzle.mail")


def send_email(recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("SMTP is not configured. Email to %s — %s\n%s", recipient, subject, body)
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except OSError:
        logger.exception("Failed to send email to %s", recipient)
        raise
