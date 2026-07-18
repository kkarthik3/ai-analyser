"""
Async batch writer for TimescaleDB.

Buffers incoming tick and option chain data, then writes in batches
for optimal hypertable insert performance. Uses a configurable flush
interval and buffer size.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.config import get_settings
from app.db.engine import get_async_session

logger = logging.getLogger(__name__)
settings = get_settings()


class SnapshotWriter:
    """Buffered async batch writer for market data.

    Accumulates tick and option chain records in memory and flushes
    them to TimescaleDB in batches for optimal write throughput.
    """

    def __init__(
        self,
        flush_interval_ms: int = 500,
        max_buffer_size: int = 5000,
    ) -> None:
        self._tick_buffer: list[dict[str, Any]] = []
        self._chain_buffer: list[dict[str, Any]] = []
        self._flush_interval = flush_interval_ms / 1000.0
        self._max_buffer_size = max_buffer_size
        self._is_running = False
        self._stats = {
            "ticks_written": 0,
            "chains_written": 0,
            "flush_count": 0,
            "errors": 0,
            "last_flush": None,
        }

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "tick_buffer_size": len(self._tick_buffer),
            "chain_buffer_size": len(self._chain_buffer),
        }

    def buffer_tick(self, tick: dict[str, Any]) -> None:
        """Add a tick record to the write buffer."""
        self._tick_buffer.append(tick)

        # Force flush if buffer is too large
        if len(self._tick_buffer) >= self._max_buffer_size:
            asyncio.create_task(self._flush_ticks())

    def buffer_chain(self, records: list[dict[str, Any]]) -> None:
        """Add option chain records to the write buffer."""
        self._chain_buffer.extend(records)

        if len(self._chain_buffer) >= self._max_buffer_size:
            asyncio.create_task(self._flush_chain())

    async def flush_loop(self) -> None:
        """Background loop that periodically flushes buffers to DB."""
        self._is_running = True
        logger.info(
            f"Snapshot writer started (flush interval: {self._flush_interval}s)"
        )

        while self._is_running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
                self._stats["errors"] += 1

    async def flush(self) -> None:
        """Flush all buffered data to the database."""
        await self._flush_ticks()
        await self._flush_chain()
        self._stats["flush_count"] += 1
        self._stats["last_flush"] = datetime.now().isoformat()

    async def _flush_ticks(self) -> None:
        """Write buffered tick data to TimescaleDB."""
        if not self._tick_buffer:
            return

        # Swap buffer to avoid holding the data while writing
        batch = self._tick_buffer[:]
        self._tick_buffer.clear()

        try:
            async with get_async_session() as session:
                from app.db.models.market_ticks import MarketTick
                await session.execute(
                    MarketTick.__table__.insert(),
                    batch,
                )
            self._stats["ticks_written"] += len(batch)
            logger.debug(f"Flushed {len(batch)} ticks to DB")
        except Exception as e:
            logger.error(f"Failed to flush {len(batch)} ticks: {e}")
            self._stats["errors"] += 1
            # Put back failed records for retry (at front of buffer)
            self._tick_buffer = batch + self._tick_buffer

    async def _flush_chain(self) -> None:
        """Write buffered option chain data to TimescaleDB."""
        if not self._chain_buffer:
            return

        batch = self._chain_buffer[:]
        self._chain_buffer.clear()

        try:
            async with get_async_session() as session:
                from app.db.models.option_chain import OptionChainSnapshot
                await session.execute(
                    OptionChainSnapshot.__table__.insert(),
                    batch,
                )
            self._stats["chains_written"] += len(batch)
            logger.debug(f"Flushed {len(batch)} option chain records to DB")
        except Exception as e:
            logger.error(f"Failed to flush {len(batch)} chain records: {e}")
            self._stats["errors"] += 1
            self._chain_buffer = batch + self._chain_buffer

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining data."""
        self._is_running = False
        await self.flush()
        logger.info("Snapshot writer stopped")
