"""M0 cancellation pipeline demo — no Redis/Postgres server required.

Run from repo root:
    python -m pip install -e "packages/intelligence[dev]"
    python -m pip install -r app/backend/requirements.txt
    $env:PYTHONPATH = "app/backend"   # PowerShell
    python app/backend/demo_m0_pipeline.py

What it shows:
  10 order.created + 3 order.cancelled in one 30-min window
  → MetricSnapshot (30% cancel rate vs 7% fixture baseline)
  → CANCELLATION_SPIKE signal
  → persisted Incident (AWAITING_APPROVAL)
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

# Ensure backend package imports resolve when run as a script
_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Base, Event, Incident, Restaurant, Signal
from src.ingestion.schemas import EventEnvelope
from src.intelligence.pipeline import run_detection_pipeline
from sqlalchemy import select


def _order_created(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_ord_{i:03d}",
        "restaurant_id": "store_17",
        "source": "pos",
        "event_type": "order.created",
        "occurred_at": "2026-08-08T12:10:00Z",
        "entity": {"type": "order", "id": f"ord_{i:03d}"},
        "data": {"channel": "delivery", "amount": 500.0, "currency": "INR"},
        "metadata": {"synthetic": True, "scenario_id": "m0_demo"},
    }


def _order_cancelled(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_cancel_{i:03d}",
        "restaurant_id": "store_17",
        "source": "pos",
        "event_type": "order.cancelled",
        "occurred_at": "2026-08-08T12:15:00Z",
        "entity": {"type": "order", "id": f"ord_{i:03d}"},
        "data": {
            "channel": "delivery",
            "amount": 500.0,
            "currency": "INR",
            "reason_code": "TOO_LONG",
        },
        "metadata": {"synthetic": True, "scenario_id": "m0_demo"},
    }


class _SessionCM:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        db.add(
            Restaurant(
                id="store_17",
                name="Demo Outlet 17",
                timezone="UTC",
                currency="INR",
                synthetic=True,
            )
        )
        await db.commit()

        print("=" * 60)
        print("  LOSSLine M0 Pipeline Demo")
        print("=" * 60)
        print("  Seeding 10 order.created + 3 order.cancelled ...")

        for i in range(1, 11):
            env = EventEnvelope(**_order_created(i))
            db.add(
                Event(
                    event_id=env.event_id,
                    restaurant_id=env.restaurant_id,
                    source=env.source.value,
                    event_type=env.event_type.value,
                    occurred_at=env.occurred_at,
                    entity=env.entity.model_dump(),
                    data=env.data,
                    metadata_json=env.metadata.model_dump(),
                    schema_version=env.schema_version,
                    payload_hash=f"hash_{env.event_id}",
                    published_to_stream=True,
                )
            )
        for i in range(1, 4):
            env = EventEnvelope(**_order_cancelled(i))
            db.add(
                Event(
                    event_id=env.event_id,
                    restaurant_id=env.restaurant_id,
                    source=env.source.value,
                    event_type=env.event_type.value,
                    occurred_at=env.occurred_at,
                    entity=env.entity.model_dump(),
                    data=env.data,
                    metadata_json=env.metadata.model_dump(),
                    schema_version=env.schema_version,
                    payload_hash=f"hash_{env.event_id}",
                    published_to_stream=True,
                )
            )
        await db.commit()

        trigger = EventEnvelope(**_order_cancelled(3))
        print(f"  Trigger event: {trigger.event_id} ({trigger.event_type.value})")
        print("-" * 60)

        with (
            patch(
                "src.intelligence.pipeline.SessionLocal",
                return_value=_SessionCM(db),
            ),
            patch(
                "src.intelligence.pipeline.broadcast_incident_transition",
                new_callable=AsyncMock,
            ),
        ):
            await run_detection_pipeline(trigger)

        signals = (
            await db.execute(select(Signal).where(Signal.signal_type == "CANCELLATION_SPIKE"))
        ).scalars().all()
        incidents = (await db.execute(select(Incident))).scalars().all()

        if not signals:
            print("  [FAIL] No CANCELLATION_SPIKE signal — check thresholds/seed.")
        else:
            sig = signals[0]
            print("  [SIGNAL] CANCELLATION_SPIKE")
            print(f"    severity       : {sig.severity}")
            print(f"    current_value  : {sig.current_value:.1%} cancel rate")
            print(f"    baseline_value : {sig.baseline_value:.1%} (M0 fixture)")
            print(f"    deviation      : {sig.deviation}")
            print(f"    window         : {sig.window_start} -> {sig.window_end}")

        if not incidents:
            print("  [FAIL] No incident persisted.")
        else:
            inc = incidents[0]
            print("  [INCIDENT]")
            print(f"    id             : {inc.id}")
            print(f"    type           : {inc.incident_type}")
            print(f"    status         : {inc.status}")
            print(f"    confidence     : {inc.confidence}")
            print(f"    explanation    : {inc.explanation}")

        print("=" * 60)
        print("  Done. Same path as Redis consumer -> run_detection_pipeline.")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
