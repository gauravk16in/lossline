from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.db.models import Event, Incident, Restaurant
from src.ingestion.schemas import EventEnvelope
from src.intelligence.m1_scenario import (
    OUTLET,
    m1_overload_payloads,
    m1_trigger_payload,
)
from src.intelligence.pipeline import run_detection_pipeline
from src.main import app
from src.demo.entities import MEGHANA_INDIRANAGAR


class SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_):
        return None


@pytest.mark.asyncio
async def test_m1_api_detection_approval_recovery_outcome(client_override, db_session):
    db_session.add(
        Restaurant(
            id=OUTLET,
            name=MEGHANA_INDIRANAGAR.name,
            timezone=MEGHANA_INDIRANAGAR.timezone,
            currency=MEGHANA_INDIRANAGAR.currency,
            synthetic=True,
            metadata_json=dict(MEGHANA_INDIRANAGAR.metadata),
        )
    )
    await db_session.commit()
    payloads = m1_overload_payloads(include_supporting=True)
    trigger_payload = m1_trigger_payload()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for payload in payloads:
            response = await client.post("/api/v1/events", json=payload)
            assert response.status_code == 202
        await db_session.commit()

        with (
            patch(
                "src.intelligence.pipeline.SessionLocal",
                return_value=SessionContext(db_session),
            ),
            patch(
                "src.intelligence.pipeline.broadcast_incident_transition",
                new_callable=AsyncMock,
            ),
        ):
            await run_detection_pipeline(EventEnvelope(**trigger_payload))

        incident = (await db_session.execute(select(Incident))).scalars().one()
        assert incident.status == "AWAITING_APPROVAL"
        assert incident.explanation

        decision = await client.post(
            f"/api/v1/incidents/{incident.id}/decision",
            json={
                "decision": "APPROVE",
                "manager_note": "Proceed with demo mitigation",
                "idempotency_key": "e2e-approval-1",
            },
        )
        assert decision.status_code == 200
        assert incident.status == "APPROVED_PENDING_EXECUTION"
        execution = await client.post(
            f"/api/v1/actions/{decision.json()['action_id']}/execution"
        )
        assert execution.status_code == 200
        assert execution.json()["execution_status"] == "EXECUTED"

        for index in range(3):
            db_session.add(
                Event(
                    event_id=f"e2e_recovery_{index}",
                    restaurant_id=OUTLET,
                    source="pos",
                    event_type="order.created",
                    occurred_at=incident.window_end + timedelta(minutes=index + 1),
                    entity={"type": "order", "id": f"recovery_order_{index}"},
                    data={"channel": "delivery", "amount": 320, "currency": "INR"},
                    metadata_json={"synthetic": True},
                    schema_version="1.0",
                    payload_hash=f"e2e_hash_{index}",
                    published_to_stream=True,
                )
            )
        await db_session.commit()

        verified = await client.post(f"/api/v1/incidents/{incident.id}/verify")
        assert verified.status_code == 200
        assert verified.json()["status"] == "IMPROVED"
        detail = await client.get(f"/api/v1/incidents/{incident.id}")
        assert detail.json()["status"] == "RESOLVED"
        summary = await client.get("/api/v1/analytics/summary")
        assert summary.json()["resolved_incident_count"] == 1
