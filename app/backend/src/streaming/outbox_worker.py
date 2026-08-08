import asyncio
import logging
from typing import cast, Any
from datetime import datetime
from sqlalchemy import select
from src.db.session import SessionLocal
from src.db.models import Event
from src.ingestion.schemas import EventEnvelope
from src.streaming.publisher import RedisPublisher

logger = logging.getLogger(__name__)


async def process_outbox(redis_publisher: RedisPublisher):
    """
    Query up to 100 unpublished events from the DB and publish them to Redis.
    Uses individual transactions for reliability.
    """
    async with SessionLocal() as session:
        # Fetch a batch of unpublished events ordered by insertion
        result = await session.execute(
            select(Event)
            .filter(Event.published_to_stream == False)
            .order_by(Event.id.asc())
            .limit(100)
        )
        events = result.scalars().all()

        if not events:
            return

        for ev in events:
            # Reconstruct the Pydantic EventEnvelope
            envelope = EventEnvelope(
                schema_version=cast(str, ev.schema_version),
                event_id=cast(str, ev.event_id),
                restaurant_id=cast(str, ev.restaurant_id),
                source=cast(Any, ev.source),
                event_type=cast(Any, ev.event_type),
                occurred_at=cast(datetime, ev.occurred_at),
                entity=cast(Any, ev.entity),
                data=cast(dict[str, Any], ev.data),
                metadata=cast(Any, ev.metadata_json),
            )

            try:
                # Publish to Redis Stream
                await redis_publisher.publish_event(envelope)

                # Mark as published in Postgres
                ev.published_to_stream = True  # type: ignore[assignment]
                await session.commit()
            except Exception as e:
                # Rollback current transaction and stop batch processing.
                # The failed event and subsequent events will be retried on next poll.
                await session.rollback()
                logger.error(
                    f"Outbox worker failed to process event {ev.event_id}. "
                    f"Transaction rolled back. Error: {e}"
                )
                break


async def start_outbox_worker(
    redis_publisher: RedisPublisher, interval_seconds: float = 1.0
):
    """
    Loop runner for the outbox worker background task.
    """
    logger.info("Outbox worker background task initialized.")
    try:
        while True:
            await process_outbox(redis_publisher)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Outbox worker task cancellation requested.")
    except Exception as e:
        logger.critical(f"Outbox worker encountered a fatal crash: {e}", exc_info=True)
        raise
