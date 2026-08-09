"""M1 operational-overload pipeline demo — no Redis/Postgres server required.

Run from repo root (PowerShell):
    $env:PYTHONPATH = "app/backend"
    python app/backend/demo_m1_pipeline.py

What it shows:
  surge orders + slow prep + cancellations (+ handoff/reviews)
  -> ORDER_VOLUME_SPIKE + PREP_TIME_SPIKE + CANCELLATION_SPIKE
  -> correlate -> OPERATIONAL_OVERLOAD incident
  -> confidence + revenue + recommendation
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from src.db.models import Base, Event, Incident, Recommendation, Restaurant, Signal
from src.ingestion.schemas import EventEnvelope
from src.intelligence.m1_scenario import (
    OUTLET,
    m1_overload_payloads,
    m1_trigger_payload,
)
from src.intelligence.pipeline import run_detection_pipeline
from src.demo.entities import MEGHANA_INDIRANAGAR


class _SessionCM:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        pass


async def _persist(db: AsyncSession, payload: dict[str, Any]) -> EventEnvelope:
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
    return envelope


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as db:
        db.add(
            Restaurant(
                id=OUTLET,
                name=MEGHANA_INDIRANAGAR.name,
                timezone=MEGHANA_INDIRANAGAR.timezone,
                currency=MEGHANA_INDIRANAGAR.currency,
                synthetic=True,
                metadata_json=dict(MEGHANA_INDIRANAGAR.metadata),
            )
        )
        await db.commit()

        payloads = m1_overload_payloads(include_supporting=True)
        print("=" * 64)
        print("  LOSSLine M1 Overload Pipeline Demo")
        print("=" * 64)
        print(f"  Seeding {len(payloads)} events for {OUTLET} ...")
        for payload in payloads:
            await _persist(db, payload)
        await db.commit()

        trigger = EventEnvelope(**m1_trigger_payload())
        print(f"  Trigger: {trigger.event_id} ({trigger.event_type.value})")
        print("-" * 64)

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

        signals = (await db.execute(select(Signal))).scalars().all()
        print(f"  Signals ({len(signals)}):")
        for sig in signals:
            print(
                f"    - {sig.signal_type:24s} severity={sig.severity:.2f} "
                f"current={sig.current_value} baseline={sig.baseline_value}"
            )

        incidents = (
            await db.execute(
                select(Incident).options(selectinload(Incident.recommendations))
            )
        ).scalars().all()

        if not incidents:
            print("  [FAIL] No OPERATIONAL_OVERLOAD incident — check seed/thresholds.")
        else:
            for inc in incidents:
                print("  [INCIDENT]")
                print(f"    id           : {inc.id}")
                print(f"    type         : {inc.incident_type}")
                print(f"    status       : {inc.status}")
                print(f"    confidence   : {inc.confidence}")
                print(f"    revenue_risk : {inc.revenue_at_risk} {inc.currency}")
                print(f"    cause        : {inc.probable_cause}")
                recs = (
                    await db.execute(
                        select(Recommendation).where(
                            Recommendation.incident_id == inc.id
                        )
                    )
                ).scalars().all()
                if not recs:
                    print("    recommendation: (none / abstention)")
                else:
                    for rec in recs:
                        print(f"    recommendation: {rec.rule_id}")
                        print(f"      urgency={rec.urgency} risk={rec.risk_tier}")
                        print(f"      action: {rec.action_text}")

        print("=" * 64)
        print("  Done. Same path as consumer -> run_detection_pipeline (M1).")
        print("=" * 64)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
