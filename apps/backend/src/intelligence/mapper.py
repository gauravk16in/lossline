"""Map backend EventEnvelope / ORM Event → intelligence NormalizedEvent.

Identity rule: restaurant_id (API/DB) maps 1:1 to outlet_id (intelligence).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from lossline_intelligence.aggregation import NormalizedEvent

from src.db.models import Event
from src.ingestion.schemas import EventEnvelope, EventType


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def envelope_to_normalized(envelope: EventEnvelope) -> NormalizedEvent:
    """Convert a validated EventEnvelope into a NormalizedEvent."""
    return _build_normalized(
        event_id=envelope.event_id,
        outlet_id=envelope.restaurant_id,
        event_type=envelope.event_type.value,
        occurred_at=envelope.occurred_at,
        data=envelope.data,
        entity_id=envelope.entity.id,
    )


def orm_event_to_normalized(event: Event) -> NormalizedEvent:
    """Convert a persisted Event row into a NormalizedEvent."""
    data = event.data if isinstance(event.data, Mapping) else {}
    return _build_normalized(
        event_id=event.event_id,
        outlet_id=event.restaurant_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        data=data,
        entity_id=(event.entity or {}).get("id"),
    )


def _build_normalized(
    *,
    event_id: str,
    outlet_id: str,
    event_type: str,
    occurred_at: datetime,
    data: Mapping[str, Any],
    entity_id: str | None,
) -> NormalizedEvent:
    channel = data.get("channel")
    amount = _decimal_or_none(data.get("amount"))
    order_id = data.get("order_id")
    duration_seconds = _float_or_none(data.get("duration_seconds"))
    wait_seconds = _float_or_none(data.get("wait_seconds"))
    rating = _int_or_none(data.get("rating"))
    text = data.get("text")
    reason_code = data.get("reason_code")

    # Only populate type-specific fields that the aggregation layer uses.
    if event_type in (
        EventType.ORDER_CREATED.value,
        EventType.ORDER_COMPLETED.value,
        EventType.ORDER_CANCELLED.value,
    ):
        order_id = None
        duration_seconds = None
        wait_seconds = None
        rating = None
        text = None
        if event_type != EventType.ORDER_CANCELLED.value:
            reason_code = None
    elif event_type == EventType.PREPARATION_COMPLETED.value:
        channel = None
        amount = None
        wait_seconds = None
        rating = None
        text = None
        reason_code = None
    elif event_type == EventType.DELIVERY_HANDOFF_COMPLETED.value:
        channel = None
        amount = None
        duration_seconds = None
        rating = None
        text = None
        reason_code = None
    elif event_type == EventType.REVIEW_RECEIVED.value:
        channel = None
        amount = None
        order_id = None
        duration_seconds = None
        wait_seconds = None
        reason_code = None
    else:
        # inventory.updated and any future types: keep identity only
        channel = None
        amount = None
        order_id = None
        duration_seconds = None
        wait_seconds = None
        rating = None
        text = None
        reason_code = None

    return NormalizedEvent(
        event_id=event_id,
        outlet_id=outlet_id,
        event_type=event_type,
        occurred_at=_as_utc(occurred_at),
        entity_id=entity_id,
        channel=str(channel) if channel is not None else None,
        amount=amount,
        order_id=str(order_id) if order_id is not None else None,
        duration_seconds=duration_seconds,
        wait_seconds=wait_seconds,
        rating=rating,
        text=str(text) if text is not None else None,
        reason_code=str(reason_code) if reason_code is not None else None,
    )
