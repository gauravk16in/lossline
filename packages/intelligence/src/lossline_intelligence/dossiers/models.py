"""C11 curated dossier serialization contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_DP = Decimal("0.0001")


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactRef(StrictFrozenModel):
    artifact_id: Identifier
    artifact_type: Identifier
    version: Identifier


class CuratedSummary(StrictFrozenModel):
    summary_id: Identifier
    summary_type: Identifier
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    evidence_ids: tuple[Identifier, ...]

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("evidence_ids must be unique")
        return value


class HistoricalPerformanceSummary(StrictFrozenModel):
    evaluation_id: Identifier
    sample_count: int
    mae: Decimal
    wmape: Decimal | None = None
    interval_coverage: Decimal | None = None

    @field_validator("mae", "wmape", "interval_coverage")
    @classmethod
    def finite_non_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite() or value < 0:
            raise ValueError("performance metrics must be finite and non-negative")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_performance(self) -> "HistoricalPerformanceSummary":
        if self.sample_count < 1:
            raise ValueError("sample_count must be positive")
        if self.interval_coverage is not None and self.interval_coverage > 1:
            raise ValueError("interval_coverage must be <= 1")
        return self


class ConstraintSummary(StrictFrozenModel):
    constraint_id: Identifier
    constraint_type: Identifier
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    evidence_id: Identifier


class DataQualitySummary(StrictFrozenModel):
    tier: Identifier
    missing_feature_ids: tuple[Identifier, ...] = ()
    imputed_feature_ids: tuple[Identifier, ...] = ()
    warnings: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def unique_items(self) -> "DataQualitySummary":
        for name in ("missing_feature_ids", "imputed_feature_ids", "warnings"):
            values = getattr(self, name)
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must be unique")
        return self


class ForecastDossier(StrictFrozenModel):
    dossier_id: Identifier
    dossier_version: Identifier
    outlet_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    prediction_as_of: datetime
    forecast_refs: tuple[ArtifactRef, ...]
    feature_snapshot_refs: tuple[ArtifactRef, ...]
    inventory_refs: tuple[ArtifactRef, ...] = ()
    capacity_refs: tuple[ArtifactRef, ...] = ()
    risk_refs: tuple[ArtifactRef, ...] = ()
    driver_refs: tuple[ArtifactRef, ...] = ()
    historical_performance: tuple[HistoricalPerformanceSummary, ...] = ()
    similar_periods: tuple[CuratedSummary, ...] = ()
    previous_decisions: tuple[CuratedSummary, ...] = ()
    constraints: tuple[ConstraintSummary, ...] = ()
    policy_refs: tuple[ArtifactRef, ...] = ()
    data_quality: DataQualitySummary
    provenance_ids: tuple[Identifier, ...]
    created_at: datetime

    @field_validator("window_start", "window_end", "prediction_as_of", "created_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_dossier(self) -> "ForecastDossier":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.prediction_as_of > self.window_start:
            raise ValueError("prediction_as_of must not be after window_start")
        if not self.forecast_refs or not self.feature_snapshot_refs:
            raise ValueError("dossier requires forecast and feature snapshot references")
        collections = (
            self.forecast_refs, self.feature_snapshot_refs, self.inventory_refs,
            self.capacity_refs, self.risk_refs, self.driver_refs, self.policy_refs,
        )
        ids = [ref.artifact_id for refs in collections for ref in refs]
        if len(set(ids)) != len(ids):
            raise ValueError("artifact references must be unique")
        if len(set(self.provenance_ids)) != len(self.provenance_ids):
            raise ValueError("provenance_ids must be unique")
        return self
