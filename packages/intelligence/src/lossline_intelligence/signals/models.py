"""Validated contracts for registry-backed predictive observations."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
JsonObject = dict[str, Any]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


class EntityType(StrEnum):
    OUTLET = "OUTLET"
    SKU = "SKU"
    ORDER = "ORDER"
    STATION = "STATION"
    STAFF_POOL = "STAFF_POOL"
    PROMOTION = "PROMOTION"
    WEATHER_REGION = "WEATHER_REGION"


class SignalCategory(StrEnum):
    DEMAND = "DEMAND"
    INVENTORY = "INVENTORY"
    CAPACITY = "CAPACITY"
    CALENDAR = "CALENDAR"
    WEATHER = "WEATHER"
    COMMERCIAL = "COMMERCIAL"
    OPERATIONS = "OPERATIONS"


class DecimalValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["DECIMAL"] = "DECIMAL"
    value: Decimal

    @field_validator("value")
    @classmethod
    def require_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("decimal signal values must be finite")
        return value


class IntegerValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["INTEGER"] = "INTEGER"
    value: int


class BooleanValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["BOOLEAN"] = "BOOLEAN"
    value: bool


class CategoricalValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["CATEGORICAL"] = "CATEGORICAL"
    value: Identifier


class TimestampValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["TIMESTAMP"] = "TIMESTAMP"
    value: datetime

    _normalize_value = field_validator("value")(_utc)


class JsonValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["JSON"] = "JSON"
    value: JsonObject

    @field_validator("value")
    @classmethod
    def require_bounded_json(cls, value: JsonObject) -> JsonObject:
        nodes = 0

        def visit(item: Any, depth: int) -> None:
            nonlocal nodes
            nodes += 1
            if nodes > 256 or depth > 8:
                raise ValueError("JSON signal values must contain at most 256 nodes and 8 levels")
            if item is None or isinstance(item, (str, bool, int)):
                return
            if isinstance(item, float):
                raise ValueError("JSON signal values cannot contain floats")
            if isinstance(item, list):
                for child in item:
                    visit(child, depth + 1)
                return
            if isinstance(item, dict):
                for key, child in item.items():
                    if not isinstance(key, str) or not key.strip():
                        raise ValueError("JSON object keys must be non-empty strings")
                    visit(child, depth + 1)
                return
            raise ValueError(f"unsupported JSON value type: {type(item).__name__}")

        visit(value, 0)
        return value


SignalValue = Annotated[
    DecimalValue
    | IntegerValue
    | BooleanValue
    | CategoricalValue
    | TimestampValue
    | JsonValue,
    Field(discriminator="kind"),
]


class SignalQuality(BaseModel):
    """Source-supplied quality; it describes evidence and never invents it."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    completeness: Annotated[Decimal, Field(ge=0, le=1)]
    validity: Annotated[Decimal, Field(ge=0, le=1)]
    freshness: Annotated[Decimal, Field(ge=0, le=1)]
    source_confidence: Annotated[Decimal, Field(ge=0, le=1)]
    is_imputed: bool = False
    issues: tuple[Identifier, ...] = ()

    @field_validator("completeness", "validity", "freshness", "source_confidence")
    @classmethod
    def require_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("quality values must be finite")
        return value

    @field_validator("issues")
    @classmethod
    def require_unique_issues(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("quality issues must be unique")
        return value


class SignalProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: Identifier
    source_record_id: Identifier
    ingested_at: datetime
    transformation_version: Identifier
    synthetic_run_id: Identifier | None = None

    _normalize_ingested_at = field_validator("ingested_at")(_utc)


class NormalizedSignal(BaseModel):
    """One immutable, registry-validated observation for predictive use."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Identifier
    signal_id: Identifier
    outlet_id: Identifier
    entity_type: EntityType
    entity_id: Identifier
    observed_at: datetime
    effective_from: datetime
    effective_until: datetime | None = None
    source: Identifier
    category: SignalCategory
    signal_type: Identifier
    value: SignalValue
    unit: Identifier
    dimensions: dict[str, str] = Field(default_factory=dict)
    metadata: JsonObject = Field(default_factory=dict)
    quality: SignalQuality
    provenance: SignalProvenance

    @field_validator("observed_at", "effective_from", "effective_until")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key.strip() or not item.strip() for key, item in value.items()):
            raise ValueError("dimension keys and values must be non-empty")
        return value

    @model_validator(mode="after")
    def require_valid_times(self) -> Self:
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from")
        if self.provenance.ingested_at < self.observed_at:
            raise ValueError("ingested_at cannot be before observed_at")
        return self
