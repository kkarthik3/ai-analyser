"""
Desktop notifications placeholder.

Since the backend runs in a headless container, this logs alerts
to standard output or hooks into the system tray when running locally.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_desktop_alert(title: str, message: str) -> bool:
    """Trigger a local desktop alert."""
    logger.warning(f"[DESKTOP ALERT] {title}: {message}")
    return True
