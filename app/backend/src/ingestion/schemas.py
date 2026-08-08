from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class EventSource(str, Enum):
    POS = "pos"
    INVENTORY = "inventory"
    DELIVERY = "delivery"
    REVIEWS = "reviews"

class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    INVENTORY_UPDATED = "inventory.updated"
    DELIVERY_HANDOFF_COMPLETED = "delivery.handoff_completed"
    ORDER_CANCELLED = "order.cancelled"
    REVIEW_RECEIVED = "review.received"

class EntitySchema(BaseModel):
    type: str = Field(..., min_length=1)  # e.g., 'order', 'restaurant'
    id: str = Field(..., min_length=1)    # e.g., 'ord_001', 'store_17'

class MetadataSchema(BaseModel):
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
class OrderCreatedData(BaseModel):
    channel: str = Field(..., min_length=1)  # e.g., 'delivery', 'dine_in', 'takeaway'
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)  # e.g., 'INR', 'USD'

class OrderCompletedData(BaseModel):
    channel: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)

class InventoryUpdatedData(BaseModel):
    sku: str = Field(..., min_length=1)
    previous_qty: float = Field(..., ge=0)
    new_qty: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1)

class DeliveryHandoffCompletedData(BaseModel):
    order_id: str = Field(..., min_length=1)
    wait_seconds: float = Field(..., ge=0)

class OrderCancelledData(BaseModel):
    channel: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    reason_code: str = Field(..., min_length=1)

class ReviewReceivedData(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1)
    language: str = Field(default="en", min_length=2)

class EventEnvelope(BaseModel):
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
            raise ValueError("occurred_at must be an ISO datetime string or datetime object")
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
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
            elif et == EventType.INVENTORY_UPDATED:
                InventoryUpdatedData(**d)
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
