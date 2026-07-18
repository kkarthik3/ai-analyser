"""
Generic async repository pattern.

Provides CRUD operations that all concrete repositories inherit.
Uses SQLAlchemy async sessions for non-blocking database access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[ModelType]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id_value: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        return await self._session.get(self._model, id_value)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ModelType]:
        """Fetch multiple records with pagination."""
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: ModelType) -> ModelType:
        """Insert a single record."""
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def create_many(self, objects: list[ModelType]) -> list[ModelType]:
        """Insert multiple records in a batch."""
        self._session.add_all(objects)
        await self._session.flush()
        return objects

    async def update(self, obj: ModelType) -> ModelType:
        """Update an existing record."""
        merged = await self._session.merge(obj)
        await self._session.flush()
        return merged

    async def delete_by_id(self, id_value: Any) -> None:
        """Delete a record by primary key."""
        obj = await self.get_by_id(id_value)
        if obj:
            await self._session.delete(obj)
            await self._session.flush()

    async def count(self) -> int:
        """Count total records."""
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def execute_query(self, stmt: Select) -> Sequence[ModelType]:
        """Execute an arbitrary select statement."""
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def bulk_insert_mappings(self, mappings: list[dict[str, Any]]) -> None:
        """High-performance bulk insert using raw mappings (bypasses ORM overhead).

        Best for high-throughput time-series data like market ticks.
        """
        if not mappings:
            return
        await self._session.execute(
            self._model.__table__.insert(),
            mappings,
        )
        await self._session.flush()
