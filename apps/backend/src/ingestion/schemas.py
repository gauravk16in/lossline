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
    SIMULATOR = "simulator"


class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    PREPARATION_COMPLETED = "preparation.completed"
    DELIVERY_HANDOFF_COMPLETED = "delivery.handoff_completed"
    ORDER_CANCELLED = "order.cancelled"
    REVIEW_RECEIVED = "review.received"
    PREDICTIVE_WINDOW_SCHEDULED = "predictive.window_scheduled"
    DEMAND_WINDOW_OBSERVED = "demand.window_observed"


class EntitySchema(ContractModel):
    type: str = Field(..., min_length=1)  # e.g., 'order', 'restaurant'
    id: str = Field(..., min_length=1)  # e.g., 'ord_001', 'meghana_indiranagar'


class MetadataSchema(ContractModel):
    synthetic: bool = False
    scenario_id: str | None = None
    scenario_run_id: str | None = Field(default=None, min_length=1, max_length=128)
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


class PredictiveSkuPlanData(ContractModel):
    sku_id: str = Field(..., min_length=1)
    base_demand: float = Field(..., ge=0)
    opening_inventory: int = Field(..., ge=0)
    replenishment_quantity: int = Field(default=0, ge=0)
    workload_minutes: float = Field(..., gt=0)


class PredictiveContext(ContractModel):
    weekday: int = Field(default=0, ge=0, le=6)
    day_of_week: str | None = Field(default=None, max_length=16)
    weather_state: str = Field(default="MISSING", min_length=1, max_length=32)
    rainfall_mm: float | None = Field(default=None, ge=0)
    holiday: bool = False
    local_event: bool = False
    promoted_sku_id: str | None = Field(default=None, max_length=128)
    promotion_discount: float | None = Field(default=None, ge=0, le=1)
    delivery_share: float = Field(default=0, ge=0, le=1)


class PredictiveWindowScheduledData(ContractModel):
    service_window: str = Field(..., min_length=1)
    window_start: datetime
    window_end: datetime
    available_capacity_minutes: float = Field(..., gt=0)
    data_quality: float = Field(..., ge=0, le=1)
    context: PredictiveContext
    skus: tuple[PredictiveSkuPlanData, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def valid_window_and_skus(self):
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("predictive window timestamps must be timezone-aware")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        ids = [item.sku_id for item in self.skus]
        if len(ids) != len(set(ids)): raise ValueError("scheduled SKU IDs must be unique")
        return self


class ObservedSkuData(ContractModel):
    sku_id: str = Field(..., min_length=1)
    actual_demand: int = Field(..., ge=0)
    fulfilled_quantity: int = Field(..., ge=0)
    unfulfilled_quantity: int = Field(..., ge=0)
    ending_inventory: int
    stockout: bool
    workload_minutes: float = Field(..., gt=0)
    opening_inventory: int = Field(..., ge=0)

    @model_validator(mode="after")
    def conserve_demand(self):
        if self.fulfilled_quantity + self.unfulfilled_quantity != self.actual_demand:
            raise ValueError("fulfilled plus unfulfilled must equal actual demand")
        return self


class DemandWindowObservedData(ContractModel):
    service_window: str = Field(..., min_length=1)
    window_start: datetime
    window_end: datetime
    capacity_utilization: float = Field(..., ge=0)
    available_capacity_minutes: float = Field(..., gt=0)
    data_quality: float = Field(..., ge=0, le=1)
    context: PredictiveContext
    skus: tuple[ObservedSkuData, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def valid_window_and_skus(self):
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("observed window timestamps must be timezone-aware")
        if self.window_end <= self.window_start: raise ValueError("window_end must be after window_start")
        ids = [item.sku_id for item in self.skus]
        if len(ids) != len(set(ids)): raise ValueError("observed SKU IDs must be unique")
        return self


class EventEnvelope(ContractModel):
    schema_version: str = Field(default="1.0")
    event_id: str = Field(..., min_length=1)
    restaurant_id: str | None = Field(default=None, min_length=1)
    outlet_id: str | None = Field(default=None, min_length=1)
    source: EventSource
    event_type: EventType
    occurred_at: datetime
    entity: EntitySchema
    data: Dict[str, Any]
    metadata: MetadataSchema

    @model_validator(mode="after")
    def resolve_outlet_identity(self) -> "EventEnvelope":
        if self.outlet_id is None and self.restaurant_id is None:
            raise ValueError("outlet_id or restaurant_id is required")
        if self.outlet_id and self.restaurant_id and self.outlet_id != self.restaurant_id:
            raise ValueError("restaurant_id and outlet_id must match during compatibility period")
        resolved = self.outlet_id or self.restaurant_id
        object.__setattr__(self, "outlet_id", resolved)
        object.__setattr__(self, "restaurant_id", resolved)
        return self

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
            elif et == EventType.PREDICTIVE_WINDOW_SCHEDULED:
                PredictiveWindowScheduledData(**d)
            elif et == EventType.DEMAND_WINDOW_OBSERVED:
                DemandWindowObservedData(**d)
            else:
                raise ValueError(f"Unrecognized event_type: {et}")
        except Exception as e:
            raise ValueError(f"Payload validation failed for type '{et.value}': {e}")

        return self
