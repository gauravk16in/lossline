import json
import logging
from redis.asyncio import Redis
from app.ingestion.schemas import EventEnvelope

logger = logging.getLogger(__name__)


class RedisPublisher:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.stream_name = "restaurant.events"

    async def publish_event(self, event_envelope: EventEnvelope) -> str:
        """
        Publishes a normalized event to the Redis Stream.
        Returns the message ID assigned by Redis.
        """
        # Convert envelope to dict, ensuring datetime objects are serialized as ISO format strings
        event_dict = event_envelope.model_dump()
        event_dict["occurred_at"] = event_envelope.occurred_at.isoformat()
        if "received_at" in event_dict:
            # Pydantic schema doesn't have received_at, but we check just in case
            event_dict["received_at"] = event_dict["received_at"].isoformat()

        payload_str = json.dumps(event_dict)

        # Write to Redis Stream
        try:
            message_id = await self.redis.xadd(
                name=self.stream_name, fields={"payload": payload_str}
            )
            msg_id_str = (
                message_id.decode("utf-8")
                if isinstance(message_id, bytes)
                else str(message_id)
            )
            logger.info(
                f"Published event {event_envelope.event_id} to stream {self.stream_name} with ID {msg_id_str}"
            )
            return msg_id_str
        except Exception as e:
            logger.error(
                f"Failed to publish event {event_envelope.event_id} to Redis: {e}"
            )
            raise
