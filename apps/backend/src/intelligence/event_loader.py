"""Load persisted events for outlet analysis windows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lossline_intelligence.aggregation import NormalizedEvent

from src.db.models import Event
from src.intelligence.mapper import orm_event_to_normalized


async def load_normalized_events(
    db: AsyncSession,
    *,
    restaurant_id: str,
    window_start: datetime,
    window_end: datetime,
) -> list[NormalizedEvent]:
    """Load events in ``[window_start, window_end)`` for one restaurant/outlet."""
    stmt = (
        select(Event)
        .where(
            Event.restaurant_id == restaurant_id,
            Event.occurred_at >= window_start,
            Event.occurred_at < window_end,
        )
        .order_by(Event.occurred_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [orm_event_to_normalized(row) for row in rows]


async def load_events_spanning(
    db: AsyncSession,
    *,
    restaurant_id: str,
    range_start: datetime,
    range_end: datetime,
) -> list[NormalizedEvent]:
    """Load all events in a wider range (for multi-window baseline rebuild)."""
    stmt = (
        select(Event)
        .where(
            Event.restaurant_id == restaurant_id,
            Event.occurred_at >= range_start,
            Event.occurred_at < range_end,
        )
        .order_by(Event.occurred_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [orm_event_to_normalized(row) for row in rows]
