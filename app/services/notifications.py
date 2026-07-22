"""Email sending with a logged stub fallback when SMTP is not configured."""
import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger("valenciaguard.mail")


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via SMTP, or log it when SMTP is not configured.

    Returns True if actually sent, False if stubbed/failed.
    """
    if not to:
        to = settings.notify_email
    if not settings.smtp_host:
        logger.info("EMAIL STUB to=%s subject=%s\n%s", to or "(none)", subject, body)
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:  # pragma: no cover - network dependent
        logger.exception("Failed to send email to %s", to)
        return False
