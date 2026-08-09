from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EventSource(str, Enum):
    POS = "pos"
    DELIVERY = "delivery"
    REVIEWS = "reviews"
    KDS = "kds"


class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    PREPARATION_COMPLETED = "preparation.completed"
    DELIVERY_HANDOFF_COMPLETED = "delivery.handoff_completed"
    ORDER_CANCELLED = "order.cancelled"
    REVIEW_RECEIVED = "review.received"


class EntitySchema(ContractModel):
    type: str = Field(..., min_length=1)  # e.g., 'order', 'restaurant'
    id: str = Field(..., min_length=1)  # e.g., 'ord_001', 'meghana_indiranagar'


class MetadataSchema(ContractModel):
    synthetic: bool = True
    scenario_id: str | None = None
    sequence: int | None = None
    schema_version: str = "1.0"

    @field_validator("schema_version", mode="before")
    @classmethod
    def coerce_schema_version(cls, v: Any) -> str:
        if v is None:
            return "1.0"
        return str(v)


# Specific payload schemas for nested validation
class OrderCreatedData(ContractModel):
    channel: str = Field(..., min_length=1)  # e.g., 'delivery', 'dine_in', 'takeaway'
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)  # e.g., 'INR', 'USD'


class OrderCompletedData(ContractModel):
    channel: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)


class PreparationCompletedData(ContractModel):
    order_id: str = Field(..., min_length=1)
    duration_seconds: float = Field(..., ge=0)


class DeliveryHandoffCompletedData(ContractModel):
    order_id: str = Field(..., min_length=1)
    wait_seconds: float = Field(..., ge=0)


class OrderCancelledData(ContractModel):
    channel: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    reason_code: str = Field(..., min_length=1)


class ReviewReceivedData(ContractModel):
    rating: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1)
    language: str = Field(default="en", min_length=2)


class EventEnvelope(ContractModel):
    schema_version: str = Field(default="1.0")
    event_id: str = Field(..., min_length=1)
    restaurant_id: str = Field(..., min_length=1)
    source: EventSource
    event_type: EventType
    occurred_at: datetime
    entity: EntitySchema
    data: Dict[str, Any]
    metadata: MetadataSchema

    @field_validator("schema_version", mode="before")
    @classmethod
    def coerce_schema_version(cls, v: Any) -> str:
        if v is None:
            return "1.0"
        return str(v)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def parse_and_normalize_utc(cls, v: Any) -> datetime:
        if isinstance(v, str):
            # Parse ISO string and handle 'Z' to UTC offset conversion if python version < 3.11
            val = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(val)
        elif isinstance(v, datetime):
            dt = v
        else:
            raise ValueError(
                "occurred_at must be an ISO datetime string or datetime object"
            )

        if dt.tzinfo is None:
            raise ValueError("occurred_at must include a timezone offset")
        return dt.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_payload_data(self) -> "EventEnvelope":
        et = self.event_type
        d = self.data

        try:
            if et == EventType.ORDER_CREATED:
                OrderCreatedData(**d)
            elif et == EventType.ORDER_COMPLETED:
                OrderCompletedData(**d)
            elif et == EventType.PREPARATION_COMPLETED:
                PreparationCompletedData(**d)
            elif et == EventType.DELIVERY_HANDOFF_COMPLETED:
                DeliveryHandoffCompletedData(**d)
            elif et == EventType.ORDER_CANCELLED:
                OrderCancelledData(**d)
            elif et == EventType.REVIEW_RECEIVED:
                ReviewReceivedData(**d)
            else:
                raise ValueError(f"Unrecognized event_type: {et}")
        except Exception as e:
            raise ValueError(f"Payload validation failed for type '{et.value}': {e}")

        return self
