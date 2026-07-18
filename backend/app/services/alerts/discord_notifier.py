"""
Discord alert notifier.
"""

from __future__ import annotations

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_discord_alert(message: str) -> bool:
    """Send alert message via Discord Webhook."""
    webhook_url = settings.discord_webhook_url

    if not webhook_url:
        logger.debug("Discord webhook not configured.")
        return False

    payload = {
        "content": message
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(webhook_url, json=payload, timeout=5.0)
            if res.status_code in (200, 204):
                logger.info("Discord alert sent successfully.")
                return True
            else:
                logger.error(f"Discord webhook error: {res.status_code} - {res.text}")
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")

    return False
