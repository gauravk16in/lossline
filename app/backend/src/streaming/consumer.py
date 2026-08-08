import asyncio
import json
import logging
from datetime import datetime, timezone
from redis.asyncio import Redis
from sqlalchemy import select
from src.ingestion.schemas import EventEnvelope
from src.db.session import SessionLocal
from src.db.models import Incident, Recommendation
from src.realtime.websocket import manager

from typing import cast, Any, List as TList, Tuple as TTuple, Dict as TDict

logger = logging.getLogger(__name__)


async def process_event_in_pipeline(envelope: EventEnvelope):
    """
    Downstream processing. Detects stockout events to raise incidents,
    and positive reviews to resolve active approved incidents.
    """
    logger.info(
        f"[Detection Pipeline] Ingested {envelope.event_type} "
        f"for restaurant {envelope.restaurant_id}. Event ID: {envelope.event_id}"
    )

    # 1. Detection rule: MEGHANA_SPECIAL_CHICKEN_BIRYANI stockout (quantity drops to 0.0)
    if envelope.event_type.value == "inventory.updated" and envelope.data.get("new_qty") == 0.0:
        sku = envelope.data.get("sku") or envelope.entity_id
        logger.info(f"[Detection Pipeline] STOCKOUT DETECTED for {sku}. Checking for existing incidents...")
        
        async with SessionLocal() as db:
            stmt = select(Incident).filter(
                Incident.restaurant_id == envelope.restaurant_id,
                Incident.incident_type == "STOCKOUT_DEGRADATION",
                Incident.status != "RESOLVED"
            )
            result = await db.execute(stmt)
            existing_incident = result.scalars().first()
            
            if not existing_incident:
                now = datetime.now(timezone.utc)
                # Create Incident
                incident = Incident(
                    restaurant_id=envelope.restaurant_id,
                    incident_type="STOCKOUT_DEGRADATION",
                    status="AWAITING_APPROVAL",
                    severity=4.0,
                    confidence=0.95,
                    confidence_components={"inventory": 1.0, "volume": 0.9},
                    probable_cause=f"Inventory Stockout of {sku} due to surge",
                    explanation=f"Demand surged 2.5x causing inventory stockout of {sku} and wait times to exceed 15 mins.",
                    revenue_at_risk=4500.0,
                    currency="INR",
                    window_start=now,
                    window_end=now,
                    correlation_rule_version="1.0",
                    config_version="1.0",
                    created_at=now
                )
                db.add(incident)
                await db.flush()  # get incident.id
                
                # Create Recommendation
                recommendation = Recommendation(
                    incident_id=incident.id,
                    rule_id="RULE_STOCKOUT_THROTTLE",
                    action_text=f"Limit delivery order rate for {sku} and increase preparation buffers.",
                    expected_impact={"revenue_saved": 3200.0, "time_to_recover": "15m"},
                    urgency="HIGH",
                    risk_tier="LOW",
                    source="RULE",
                    expires_at=now,
                    created_at=now
                )
                db.add(recommendation)
                await db.commit()
                logger.info(f"[Detection Pipeline] Created incident {incident.id} and recommendation {recommendation.id}")
                
                # Broadcast WebSocket update
                await manager.broadcast_transition(
                    {
                        "message_id": f"msg_inc_new_{incident.id}",
                        "incident_id": incident.id,
                        "stage": "AWAITING_APPROVAL",
                        "status": "success",
                        "occurred_at": now.isoformat()
                    }
                )

    # 2. Resolution rule: Customer positive review received in recovery phase
    elif envelope.event_type.value == "review.received" and envelope.data.get("rating", 0) >= 4.0:
        logger.info(f"[Detection Pipeline] Positive review detected. Checking to resolve active approved incidents...")
        async with SessionLocal() as db:
            stmt = select(Incident).filter(
                Incident.restaurant_id == envelope.restaurant_id,
                Incident.status == "ACTION_APPROVED"
            )
            result = await db.execute(stmt)
            incident = result.scalars().first()
            
            if incident:
                logger.info(f"[Detection Pipeline] Recovery verified. Resolving incident {incident.id}...")
                incident.status = "RESOLVED"
                await db.commit()
                
                # Broadcast transition
                await manager.broadcast_transition(
                    {
                        "message_id": f"msg_inc_res_{incident.id}",
                        "incident_id": incident.id,
                        "stage": "RESOLVED",
                        "status": "success",
                        "occurred_at": datetime.now(timezone.utc).isoformat()
                    }
                )


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
