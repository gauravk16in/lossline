import asyncio
import pytest
import json
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Event, Restaurant
from src.ingestion.schemas import EventEnvelope
from src.streaming.publisher import RedisPublisher
from src.streaming.outbox_worker import process_outbox
from src.streaming.consumer import start_redis_consumer
from tests.conftest import MockRedisClient

VALID_EVENT_DICT: dict[str, Any] = {
    "schema_version": "1.0",
    "event_id": "evt_outbox_777",
    "restaurant_id": "store_17",
    "source": "pos",
    "event_type": "order.created",
    "occurred_at": "2026-08-08T15:30:00Z",
    "entity": {"type": "order", "id": "ord_777"},
    "data": {"channel": "delivery", "amount": 100.0, "currency": "INR"},
    "metadata": {"synthetic": True, "scenario_id": "test_scenario"},
}


@pytest.mark.asyncio
async def test_transactional_outbox_and_stream_pipeline(
    db_session: AsyncSession, mock_redis: MockRedisClient
) -> None:
    # 1. Setup seed restaurant outlet
    restaurant = Restaurant(
        id="store_17", name="Outlet 17", timezone="UTC", currency="INR", synthetic=True
    )
    db_session.add(restaurant)
    await db_session.commit()

    # 2. Add event in Postgres with published_to_stream = False
    envelope = EventEnvelope(**VALID_EVENT_DICT)
    event_record = Event(
        event_id=envelope.event_id,
        restaurant_id=envelope.restaurant_id,
        source=envelope.source.value,
        event_type=envelope.event_type.value,
        occurred_at=envelope.occurred_at,
        entity=envelope.entity.model_dump(),
        data=envelope.data,
        metadata_json=envelope.metadata.model_dump(),
        schema_version=envelope.schema_version,
        payload_hash="dummy_hash_777",
        published_to_stream=False,
    )
    db_session.add(event_record)
    await db_session.commit()

    # Verify event is in DB as unpublished
    result = await db_session.execute(
        select(Event).filter(Event.event_id == "evt_outbox_777")
    )
    event_db = result.scalars().first()
    assert event_db is not None
    assert event_db.published_to_stream is False

    # 3. Instantiate RedisPublisher with MockRedis and run outbox worker processor
    publisher = RedisPublisher(mock_redis)
    # We patch SessionLocal inside outbox_worker to yield our transactional db_session
    # so it targets the in-memory test database instead of production
    import src.streaming.outbox_worker
    from unittest.mock import patch

    # We create a mock context manager for session
    class AsyncContextManagerMock:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session

        async def __aenter__(self) -> AsyncSession:
            return self.session

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            pass

    with patch.object(
        src.streaming.outbox_worker,
        "SessionLocal",
        return_value=AsyncContextManagerMock(db_session),
    ):
        await process_outbox(publisher)

    # 4. Verify DB was updated to published_to_stream = True
    await db_session.refresh(event_db)
    assert event_db.published_to_stream is True

    # 5. Verify the event made it to the Redis stream
    assert "restaurant.events" in mock_redis.streams
    assert len(mock_redis.streams["restaurant.events"]) == 1

    msg_id, fields = mock_redis.streams["restaurant.events"][0]
    payload = json.loads(fields["payload"])
    assert payload["event_id"] == "evt_outbox_777"
    assert payload["restaurant_id"] == "store_17"

    # 6. Verify Redis Stream Consumer reads and acknowledges the message.
    # Patch SessionLocal so detection pipeline uses the test DB session.
    with patch(
        "src.intelligence.pipeline.SessionLocal",
        return_value=AsyncContextManagerMock(db_session),
    ):
        consumer_task = asyncio.create_task(start_redis_consumer(mock_redis))
        await asyncio.sleep(0.2)
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    # Verify message is acknowledged and read from the mock stream
    assert (
        len(mock_redis.streams["restaurant.events"]) == 0
    )  # Consumer reads and clears the mock stream queue
