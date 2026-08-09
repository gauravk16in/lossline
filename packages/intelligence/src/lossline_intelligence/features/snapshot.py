"""Immutable point-in-time feature snapshots and dataset rows.

FeatureSnapshot is a Pydantic serialization boundary (C01 contract).
DatasetRow and fingerprint helpers are internal domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_DP = Decimal("0.0001")

PIPELINE_VERSION = "feature_pipeline.v1"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


class SnapshotQuality(BaseModel):
    """Quality metadata for one feature snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    completeness: Annotated[Decimal, Field(ge=0, le=1)]
    data_sufficiency: bool
    stale_feature_ids: tuple[str, ...] = ()
    censored_target: bool = False
    data_quality_score: Annotated[Decimal, Field(ge=0, le=1)] = Decimal("1")

    @field_validator("completeness", "data_quality_score")
    @classmethod
    def require_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("quality values must be finite")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)


class FeatureSnapshot(BaseModel):
    """Immutable point-in-time model input for one outlet × SKU × service window.

    This is a Pydantic serialization boundary following the C01 FeatureSnapshot
    contract.  Feature values are keyed by registered feature_id.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: Identifier
    pipeline_version: Identifier
    prediction_as_of: datetime
    outlet_id: Identifier
    sku_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    registry_version: Identifier
    registry_fingerprint: str
    # Values: bool checked before int to avoid subclass coercion
    feature_values: dict[str, bool | int | Decimal | str | None]
    source_signal_ids: tuple[Identifier, ...] = ()
    missing_features: tuple[Identifier, ...]
    imputed_features: tuple[Identifier, ...]
    quality: SnapshotQuality
    fingerprint: str
    created_at: datetime

    @field_validator("prediction_as_of", "window_start", "window_end", "created_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def require_valid_window(self) -> FeatureSnapshot:
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


@dataclass(frozen=True)
class DatasetRow:
    """One training/evaluation row: snapshot features plus target and censoring."""

    snapshot: FeatureSnapshot
    target_demand_quantity: int
    observed_demand_quantity: int
    censored: bool


# ---------------------------------------------------------------------------
# Deterministic fingerprinting
# ---------------------------------------------------------------------------


def _serialize_value(value: bool | int | Decimal | str | None) -> dict[str, object]:
    """Encode one feature value for deterministic hashing."""
    if isinstance(value, bool):
        return {"t": "b", "v": value}
    if isinstance(value, int):
        return {"t": "i", "v": value}
    if isinstance(value, Decimal):
        return {"t": "d", "v": str(value)}
    if isinstance(value, str):
        return {"t": "s", "v": value}
    if value is None:
        return {"t": "n", "v": None}
    raise ValueError(f"unsupported feature value type: {type(value).__name__}")


def compute_fingerprint(
    feature_values: dict[str, bool | int | Decimal | str | None],
    pipeline_version: str,
    registry_fingerprint: str,
) -> str:
    """Deterministic SHA-256 of feature values and provenance."""
    serialized = {k: _serialize_value(feature_values[k]) for k in sorted(feature_values)}
    payload = {
        "pv": pipeline_version,
        "rf": registry_fingerprint,
        "fv": serialized,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_snapshot_id(
    outlet_id: str,
    sku_id: str,
    service_window: str,
    window_start: datetime,
    prediction_as_of: datetime,
    pipeline_version: str,
) -> str:
    """Deterministic snapshot identifier from grain and temporal coordinates."""
    payload = {
        "o": outlet_id,
        "pa": prediction_as_of.isoformat(),
        "pv": pipeline_version,
        "s": sku_id,
        "w": service_window,
        "ws": window_start.isoformat(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tag = sha256(encoded).hexdigest()[:16]
    return f"snap_{outlet_id}_{sku_id}_{tag}"


def compute_dataset_fingerprint(rows: tuple[DatasetRow, ...]) -> str:
    """Deterministic SHA-256 of ordered features, targets, and censoring state."""
    encoded = json.dumps(
        [
            {
                "snapshot": row.snapshot.fingerprint,
                "target": row.target_demand_quantity,
                "observed": row.observed_demand_quantity,
                "censored": row.censored,
            }
            for row in rows
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
