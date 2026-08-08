"""Validated output contract for deterministic anomaly detectors."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Severity(StrEnum):
    """Categorical severity band shared by all deterministic detectors."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_SCORE: dict[Severity, float] = {
    Severity.LOW: 0.25,
    Severity.MEDIUM: 0.50,
    Severity.HIGH: 0.75,
    Severity.CRITICAL: 0.95,
}


class SignalType(StrEnum):
    """Signal types frozen for the M1 lunch-rush scenario."""

    ORDER_VOLUME_SPIKE = "ORDER_VOLUME_SPIKE"
    PREP_TIME_SPIKE = "PREP_TIME_SPIKE"
    HANDOFF_DELAY_SPIKE = "HANDOFF_DELAY_SPIKE"
    CANCELLATION_SPIKE = "CANCELLATION_SPIKE"
    DELAY_REVIEW_SPIKE = "DELAY_REVIEW_SPIKE"


class Signal(BaseModel):
    """Deterministic anomaly detected for one outlet and analysis window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_id: Identifier
    outlet_id: Identifier
    signal_type: SignalType
    severity: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    current_value: Decimal
    baseline_value: Decimal
    deviation_ratio: Annotated[
        Decimal,
        Field(description="Relative change: (current_value - baseline_value) / baseline_value"),
    ]
    unit: Identifier
    window_start: datetime
    window_end: datetime
    evidence_event_ids: tuple[Identifier, ...] = Field(min_length=1)
    detector_version: Identifier
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("current_value", "baseline_value", "deviation_ratio")
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

    @field_validator("evidence_event_ids")
    @classmethod
    def require_unique_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("evidence event IDs must be unique")
        return value

    @model_validator(mode="after")
    def require_valid_window(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self
