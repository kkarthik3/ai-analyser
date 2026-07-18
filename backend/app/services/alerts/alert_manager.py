"""
Alert Manager.

Central dispatcher distributing critical platform alerts to all configured channels:
Telegram, Discord, Email, and Desktop alerts.
"""

from __future__ import annotations

import asyncio
import logging

from app.services.alerts.telegram_notifier import send_telegram_alert
from app.services.alerts.discord_notifier import send_discord_alert
from app.services.alerts.email_notifier import send_email_alert
from app.services.alerts.desktop_notifier import send_desktop_alert

logger = logging.getLogger(__name__)


class AlertManager:
    """Dispatches notifications across all alert integrations in parallel."""

    def __init__(self) -> None:
        pass

    async def trigger_alert(self, title: str, message: str) -> None:
        """
        Send an alert to all configured notification channels asynchronously.
        """
        logger.info(f"Triggering alerts for: {title}")
        full_message = f"<b>{title}</b>\n\n{message}"

        # Run notifications in parallel
        await asyncio.gather(
            send_telegram_alert(full_message),
            send_discord_alert(f"**{title}**\n{message}"),
            send_desktop_alert(title, message),
            # Email is synchronous SMTP, run it in thread pool
            asyncio.get_event_loop().run_in_executor(
                None,
                send_email_alert,
                title,
                message
            ),
            return_exceptions=True
        )
