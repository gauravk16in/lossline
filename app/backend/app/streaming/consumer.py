import asyncio
import json
import logging
from redis.asyncio import Redis
from app.ingestion.schemas import EventEnvelope

from typing import cast, Any, List as TList, Tuple as TTuple, Dict as TDict

logger = logging.getLogger(__name__)


async def process_event_in_pipeline(envelope: EventEnvelope):
    """
    Placeholder for downstream deterministic metrics and detectors.
    This will interface with services/intelligence package in the next phase.
    """
    logger.info(
        f"[Detection Pipeline] Ingested {envelope.event_type} "
        f"for restaurant {envelope.restaurant_id}. Event ID: {envelope.event_id}"
    )
    # Simulate routing through specialist nodes
    await asyncio.sleep(0.01)


async def start_redis_consumer(
    redis_client: Redis,
    group_name: str = "detection",
    consumer_name: str = "backend_worker_1",
):
    """
    Background worker loop that reads and processes events from the Redis Stream.
    """
    stream_name = "restaurant.events"

    # 1. Setup stream and group if not already present
    try:
        await redis_client.xgroup_create(
            name=stream_name, groupname=group_name, id="0", mkstream=True
        )
        logger.info(
            f"Registered Redis consumer group '{group_name}' on stream '{stream_name}'"
        )
    except Exception as e:
        # Group already exists error is caught and ignored
        if "BUSYGROUP" in str(e):
            logger.debug(f"Redis consumer group '{group_name}' already exists.")
        else:
            logger.warning(f"Error during Redis stream/group setup: {e}")

    logger.info(f"Redis stream consumer initialized on '{stream_name}'")

    try:
        while True:
            # Read messages from the stream
            # Count=10, Block=1000ms (waits up to 1s if no messages are present)
            try:
                streams_to_read: TDict[str | bytes, str | bytes | int] = {
                    stream_name: ">"
                }  # Read pending/new messages for this group
                raw_response = await redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams=streams_to_read,
                    count=10,
                    block=1000,
                )

                if not raw_response:
                    await asyncio.sleep(0.1)
                    continue

                response = cast(
                    TList[
                        TTuple[
                            bytes | str,
                            TList[TTuple[bytes | str, TDict[bytes | str, bytes | str]]],
                        ]
                    ],
                    raw_response,
                )
                for stream, messages in response:
                    for msg_id, fields in messages:
                        payload_bytes = (
                            fields.get(b"payload")
                            if b"payload" in fields
                            else fields.get("payload")
                        )

                        if not payload_bytes:
                            logger.warning(
                                f"Message {msg_id} contains no payload. Acknowledging to discard."
                            )
                            await redis_client.xack(stream_name, group_name, msg_id)
                            continue

                        try:
                            # Parse envelope from JSON payload
                            payload_str = (
                                payload_bytes.decode("utf-8")
                                if isinstance(payload_bytes, bytes)
                                else payload_bytes
                            )
                            payload_dict = json.loads(payload_str)
                            envelope = EventEnvelope(**payload_dict)

                            # Process event in downstream logic
                            await process_event_in_pipeline(envelope)

                            # Acknowledge the message upon successful execution
                            await redis_client.xack(stream_name, group_name, msg_id)
                        except Exception as inner_err:
                            logger.error(
                                f"Failed to process message {msg_id}. "
                                f"Acknowledging to prevent poison block. Error: {inner_err}"
                            )
                            # In production we would publish to a dead-letter queue (DLQ)
                            # to investigate further, and xack to not block.
                            await redis_client.xack(stream_name, group_name, msg_id)

            except Exception as loop_err:
                logger.error(f"Error in Redis consumer read iteration: {loop_err}")
                await asyncio.sleep(1.0)

    except asyncio.CancelledError:
        logger.info("Redis consumer task received cancellation request.")
    except Exception as fatal_err:
        logger.critical(f"Redis consumer task crashed: {fatal_err}", exc_info=True)
        raise
