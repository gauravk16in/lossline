import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.ingestion.schemas import EventEnvelope, EventSource, EventType

# Example valid events for tests
VALID_ORDER_CREATED = {
    "schema_version": "1.0",
    "event_id": "evt_test_101",
    "restaurant_id": "store_17",
    "source": "pos",
    "event_type": "order.created",
    "occurred_at": "2026-08-08T15:30:00Z",
    "entity": {"type": "order", "id": "ord_999"},
    "data": {"channel": "delivery", "amount": 540.0, "currency": "INR"},
    "metadata": {"synthetic": True, "scenario_id": "test_scenario"},
}


def test_canonical_envelope_validation():
    # Valid payload should parse correctly
    envelope = EventEnvelope(**VALID_ORDER_CREATED)
    assert envelope.event_id == "evt_test_101"
    assert envelope.source == EventSource.POS
    assert envelope.event_type == EventType.ORDER_CREATED
    assert envelope.occurred_at.tzname() == "UTC"  # Normalized to UTC timezone

    # Invalid event_type should fail validation
    invalid_payload = VALID_ORDER_CREATED.copy()
    invalid_payload["event_type"] = "order.shipped"
    with pytest.raises(ValueError):
        EventEnvelope(**invalid_payload)

    # Negative amount should fail validation for order.created
    invalid_data = VALID_ORDER_CREATED.copy()
    invalid_data["data"] = {"channel": "delivery", "amount": -10.0, "currency": "INR"}
    with pytest.raises(ValueError):
        EventEnvelope(**invalid_data)

    naive = VALID_ORDER_CREATED | {"occurred_at": "2026-08-08T15:30:00"}
    with pytest.raises(ValueError):
        EventEnvelope(**naive)

    extra = VALID_ORDER_CREATED | {"unexpected": True}
    with pytest.raises(ValueError):
        EventEnvelope(**extra)


@pytest.mark.asyncio
async def test_api_event_ingestion_endpoint(client_override, db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Ingest a new event
        response = await ac.post("/api/v1/events", json=VALID_ORDER_CREATED)
        assert response.status_code == 202
        resp_json = response.json()
        assert resp_json["event_id"] == "evt_test_101"
        assert resp_json["duplicate"] is False

        # 2. Ingest identical duplicate -> expect 202 with duplicate = True
        response_dup = await ac.post("/api/v1/events", json=VALID_ORDER_CREATED)
        assert response_dup.status_code == 202
        assert response_dup.json()["duplicate"] is True

        # 3. Ingest duplicate event ID but with a modified payload -> expect 409 Conflict
        conflicting_payload = VALID_ORDER_CREATED.copy()
        conflicting_payload["restaurant_id"] = "store_99"  # Modified field
        response_conf = await ac.post("/api/v1/events", json=conflicting_payload)
        assert response_conf.status_code == 409
        assert (
            "already exists with a different payload" in response_conf.json()["detail"]
        )
