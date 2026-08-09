"""Tests for backend ↔ intelligence integration (M0 cancellation + helpers)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Event, Incident, Restaurant, Signal
from src.ingestion.schemas import EventEnvelope, EventType
from src.intelligence.mapper import envelope_to_normalized
from src.intelligence.pipeline import run_detection_pipeline
from src.intelligence.windows import analysis_window, prior_windows


def _order_created(i: int, occurred_at: str = "2026-08-08T12:10:00Z") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_ord_{i:03d}",
        "restaurant_id": "store_17",
        "source": "pos",
        "event_type": "order.created",
        "occurred_at": occurred_at,
        "entity": {"type": "order", "id": f"ord_{i:03d}"},
        "data": {"channel": "delivery", "amount": 500.0, "currency": "INR"},
        "metadata": {"synthetic": True, "scenario_id": "m0_cancel"},
    }


def _order_cancelled(
    i: int, occurred_at: str = "2026-08-08T12:15:00Z"
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_cancel_{i:03d}",
        "restaurant_id": "store_17",
        "source": "pos",
        "event_type": "order.cancelled",
        "occurred_at": occurred_at,
        "entity": {"type": "order", "id": f"ord_{i:03d}"},
        "data": {
            "channel": "delivery",
            "amount": 500.0,
            "currency": "INR",
            "reason_code": "TOO_LONG",
        },
        "metadata": {"synthetic": True, "scenario_id": "m0_cancel"},
    }


def test_preparation_completed_envelope_validates() -> None:
    envelope = EventEnvelope(
        **{
            "schema_version": "1.0",
            "event_id": "evt_prep_1",
            "restaurant_id": "store_17",
            "source": "kds",
            "event_type": "preparation.completed",
            "occurred_at": "2026-08-08T12:20:00Z",
            "entity": {"type": "order", "id": "ord_001"},
            "data": {"order_id": "ord_001", "duration_seconds": 900.0},
            "metadata": {"synthetic": True},
        }
    )
    assert envelope.event_type == EventType.PREPARATION_COMPLETED
    normalized = envelope_to_normalized(envelope)
    assert normalized.outlet_id == "store_17"
    assert normalized.event_type == "preparation.completed"
    assert normalized.duration_seconds == 900.0
    assert normalized.order_id == "ord_001"


def test_analysis_window_alignment() -> None:
    ts = datetime(2026, 8, 8, 12, 17, tzinfo=timezone.utc)
    start, end = analysis_window(ts, window_minutes=30)
    assert start == datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 8, 12, 30, tzinfo=timezone.utc)
    priors = prior_windows(start, count=2, window_minutes=30)
    assert len(priors) == 2
    assert priors[-1][1] == start


class AsyncContextManagerMock:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass


async def _seed_restaurant(db: AsyncSession) -> None:
    db.add(
        Restaurant(
            id="store_17",
            name="Outlet 17",
            timezone="UTC",
            currency="INR",
            synthetic=True,
        )
    )
    await db.commit()


async def _persist_envelope(db: AsyncSession, payload: dict[str, Any]) -> EventEnvelope:
    envelope = EventEnvelope(**payload)
    db.add(
        Event(
            event_id=envelope.event_id,
            restaurant_id=envelope.restaurant_id,
            source=envelope.source.value,
            event_type=envelope.event_type.value,
            occurred_at=envelope.occurred_at,
            entity=envelope.entity.model_dump(),
            data=envelope.data,
            metadata_json=envelope.metadata.model_dump(),
            schema_version=envelope.schema_version,
            payload_hash=f"hash_{envelope.event_id}",
            published_to_stream=True,
        )
    )
    await db.commit()
    return envelope


@pytest.mark.asyncio
async def test_pipeline_persists_cancellation_signal_and_incident(
    db_session: AsyncSession,
) -> None:
    await _seed_restaurant(db_session)

    # 10 orders + 3 cancellations → 30% rate vs 7% fixture baseline
    for i in range(1, 11):
        await _persist_envelope(db_session, _order_created(i))
    for i in range(1, 4):
        await _persist_envelope(db_session, _order_cancelled(i))

    trigger = EventEnvelope(**_order_cancelled(3))

    with (
        patch(
            "src.intelligence.pipeline.SessionLocal",
            return_value=AsyncContextManagerMock(db_session),
        ),
        patch(
            "src.intelligence.pipeline.broadcast_incident_transition",
            new_callable=AsyncMock,
        ) as broadcast,
    ):
        await run_detection_pipeline(trigger)

    signals = (
        (
            await db_session.execute(
                select(Signal).where(Signal.signal_type == "CANCELLATION_SPIKE")
            )
        )
        .scalars()
        .all()
    )
    assert len(signals) == 1
    assert signals[0].restaurant_id == "store_17"
    assert signals[0].deviation is not None
    assert signals[0].baseline_value == Decimal("0.0700")

    incidents = (await db_session.execute(select(Incident))).scalars().all()
    assert len(incidents) == 1
    assert incidents[0].incident_type == "CANCELLATION_SPIKE"
    assert incidents[0].status == "AWAITING_APPROVAL"
    broadcast.assert_awaited()


@pytest.mark.asyncio
async def test_pipeline_idempotent_signal_upsert(db_session: AsyncSession) -> None:
    await _seed_restaurant(db_session)
    for i in range(1, 11):
        await _persist_envelope(db_session, _order_created(i))
    for i in range(1, 4):
        await _persist_envelope(db_session, _order_cancelled(i))

    trigger = EventEnvelope(**_order_cancelled(3))
    with (
        patch(
            "src.intelligence.pipeline.SessionLocal",
            return_value=AsyncContextManagerMock(db_session),
        ),
        patch(
            "src.intelligence.pipeline.broadcast_incident_transition",
            new_callable=AsyncMock,
        ),
    ):
        await run_detection_pipeline(trigger)
        await run_detection_pipeline(trigger)

    signals = (
        (
            await db_session.execute(
                select(Signal).where(Signal.signal_type == "CANCELLATION_SPIKE")
            )
        )
        .scalars()
        .all()
    )
    assert len(signals) == 1

    incidents = (await db_session.execute(select(Incident))).scalars().all()
    assert len(incidents) == 1


@pytest.mark.asyncio
async def test_mapper_restaurant_id_becomes_outlet_id() -> None:
    envelope = EventEnvelope(**_order_created(1))
    normalized = envelope_to_normalized(envelope)
    assert normalized.outlet_id == envelope.restaurant_id
    assert normalized.amount == Decimal("500.0")


@pytest.mark.asyncio
async def test_pipeline_persists_operational_overload_incident(
    db_session: AsyncSession,
) -> None:
    """M1: volume + prep + cancel -> OPERATIONAL_OVERLOAD + recommendation."""
    from src.db.models import Recommendation
    from src.intelligence.m1_scenario import (
        OUTLET,
        m1_overload_payloads,
        m1_trigger_payload,
    )

    db_session.add(
        Restaurant(
            id=OUTLET,
            name="Outlet 17",
            timezone="UTC",
            currency="INR",
            synthetic=True,
        )
    )
    await db_session.commit()

    for payload in m1_overload_payloads(include_supporting=True):
        await _persist_envelope(db_session, payload)

    trigger = EventEnvelope(**m1_trigger_payload())
    with (
        patch(
            "src.intelligence.pipeline.SessionLocal",
            return_value=AsyncContextManagerMock(db_session),
        ),
        patch(
            "src.intelligence.pipeline.broadcast_incident_transition",
            new_callable=AsyncMock,
        ) as broadcast,
    ):
        await run_detection_pipeline(trigger)

    signal_types = {
        row.signal_type
        for row in (await db_session.execute(select(Signal))).scalars().all()
    }
    assert "ORDER_VOLUME_SPIKE" in signal_types
    assert "PREP_TIME_SPIKE" in signal_types
    assert "CANCELLATION_SPIKE" in signal_types

    incidents = (await db_session.execute(select(Incident))).scalars().all()
    assert len(incidents) == 1
    assert incidents[0].incident_type == "OPERATIONAL_OVERLOAD"
    assert incidents[0].status == "AWAITING_APPROVAL"
    assert incidents[0].confidence >= 0.50
    assert incidents[0].revenue_at_risk is not None

    recs = (
        (
            await db_session.execute(
                select(Recommendation).where(
                    Recommendation.incident_id == incidents[0].id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(recs) == 1
    assert recs[0].rule_id == "OPERATIONAL_OVERLOAD_V1"
    broadcast.assert_awaited()
