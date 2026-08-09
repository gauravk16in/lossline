import asyncio
import logging
from typing import cast, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from sqlalchemy import select
from src.db.session import SessionLocal
from src.db.models import Event
from src.ingestion.schemas import EventEnvelope
from src.streaming.publisher import RedisPublisher

logger = logging.getLogger(__name__)


async def process_outbox(redis_publisher: RedisPublisher):
    """
    Query up to 100 unpublished events from the DB and publish them to Redis.
    Uses batch commits for high throughput over high-latency WAN connections.
    """
    async with SessionLocal() as session:
        # Fetch a batch of unpublished events ordered by insertion
        stale_before = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await session.execute(
            select(Event)
            .filter(Event.published_to_stream == False)
            .filter(or_(Event.outbox_claimed_at.is_(None), Event.outbox_claimed_at < stale_before))
            .order_by(Event.id.asc())
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        events = result.scalars().all()

        if not events:
            return

        claimed_at = datetime.now(timezone.utc)
        for event in events:
            event.outbox_claimed_at = claimed_at
            event.outbox_attempt_count = int(event.outbox_attempt_count or 0) + 1
        await session.commit()

        published_ids = []
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
                ev.published_to_stream = True  # type: ignore[assignment]
                ev.outbox_published_at = datetime.now(timezone.utc)
                ev.outbox_claimed_at = None
                ev.outbox_last_error = None
                published_ids.append(ev.id)
            except Exception as e:
                ev.outbox_last_error = str(e)[:1000]
                ev.outbox_claimed_at = None
                logger.error(
                    f"Outbox worker failed to publish event {ev.event_id} to Redis: {e}"
                )
                # Stop processing subsequent events in this batch
                break

        if published_ids:
            try:
                await session.commit()
                logger.info(
                    f"Successfully committed outbox status for {len(published_ids)} events."
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to commit outbox status in database: {e}")


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
