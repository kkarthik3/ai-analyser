"""
Telegram alert notifier.
"""

from __future__ import annotations

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_telegram_alert(message: str) -> bool:
    """Send alert message via Telegram Bot API."""
    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not bot_token or not chat_id:
        logger.debug("Telegram alerts not configured (tokens missing).")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=5.0)
            if res.status_code == 200:
                logger.info("Telegram alert sent successfully.")
                return True
            else:
                logger.error(f"Telegram alert API error: {res.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")

    return False
