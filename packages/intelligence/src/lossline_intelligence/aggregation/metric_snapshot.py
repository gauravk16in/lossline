"""Aggregated operational metrics for a single outlet analysis window.

Moved from the stray lossline_intelligence/aggregation/ tree into the
installed src/ layout.  Content is unchanged from the original model.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonNegativeCount = Annotated[int, Field(ge=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]


class MetricSnapshot(BaseModel):
    """Aggregated metrics for one outlet during one analysis window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outlet_id: Identifier

    window_start: datetime
    window_end: datetime

    order_count: NonNegativeCount
    delivery_order_count: NonNegativeCount

    cancelled_order_count: NonNegativeCount
    cancellation_rate: Annotated[Decimal, Field(ge=0, le=1)]

    avg_prep_minutes: NonNegativeDecimal
    p90_prep_minutes: NonNegativeDecimal
    prep_completed_count: NonNegativeCount

    avg_handoff_wait_minutes: NonNegativeDecimal
    handoff_completed_count: NonNegativeCount

    review_count: NonNegativeCount
    negative_review_count: NonNegativeCount
    delay_review_count: NonNegativeCount
    delay_review_event_ids: tuple[Identifier, ...]

    source_event_ids: tuple[Identifier, ...]

    @field_validator(
        "cancellation_rate",
        "avg_prep_minutes",
        "p90_prep_minutes",
        "avg_handoff_wait_minutes",
    )
    @classmethod
    def require_finite_decimal(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("metric values must be finite")
        return value

    @field_validator("window_start", "window_end")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(timezone.utc)

    @field_validator("source_event_ids", "delay_review_event_ids")
    @classmethod
    def require_unique_event_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("event IDs must be unique")
        return value

    @model_validator(mode="after")
    def require_consistent_snapshot(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.delivery_order_count > self.order_count:
            raise ValueError("delivery_order_count cannot exceed order_count")
        if self.cancelled_order_count > self.order_count:
            raise ValueError("cancelled_order_count cannot exceed order_count")
        if self.negative_review_count > self.review_count:
            raise ValueError("negative_review_count cannot exceed review_count")
        if self.delay_review_count > self.review_count:
            raise ValueError("delay_review_count cannot exceed review_count")
        return self
