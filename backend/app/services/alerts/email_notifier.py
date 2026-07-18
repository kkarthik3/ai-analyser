"""
Email alert notifier.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_email_alert(subject: str, message: str) -> bool:
    """Send alert email via SMTP."""
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_pass = settings.smtp_password
    to_email = settings.alert_email_to

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, to_email]):
        logger.debug("Email alert parameters not fully configured.")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        logger.info("Email alert sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

    return False
