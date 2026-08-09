"""Forecast evaluation records, metrics, subgroup checks, and acceptance gate."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from hashlib import sha256
import json
from math import sqrt
from typing import Annotated, Sequence

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
EVALUATION_VERSION = "forecast_evaluation.v1"
PRIMARY_IMPROVEMENT_REQUIRED = Decimal("0.0500")
MAX_SUBGROUP_REGRESSION = Decimal("0.1000")


class ForecastModelKind(StrEnum):
    BASELINE = "BASELINE"
    GBT = "GBT"


class EvaluationStatus(StrEnum):
    EVALUATED = "EVALUATED"
    CENSORED = "CENSORED"
    ABSTAINED = "ABSTAINED"


class DemandBand(StrEnum):
    ZERO = "ZERO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AcceptanceStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ForecastEvaluationRow(BaseModel):
    """One forecast aligned with its matured actual at identical grain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: Identifier
    evaluation_version: Identifier
    model_kind: ForecastModelKind
    forecast_id: Identifier | None
    model_version: Identifier | None
    training_cutoff: datetime | None
    prediction_as_of: datetime
    window_start: datetime
    window_end: datetime
    outlet_id: Identifier
    sku_id: Identifier
    service_window: Identifier
    demand_band: DemandBand | None
    status: EvaluationStatus
    prediction: Decimal | None
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    actual: Decimal | None
    absolute_error: Decimal | None
    percentage_error: Decimal | None
    signed_error: Decimal | None
    interval_hit: bool | None
    abstention_reason: str | None = None

    @field_validator(
        "prediction_as_of", "window_start", "window_end", "training_cutoff"
    )
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(timezone.utc)

    @field_validator(
        "prediction",
        "lower_bound",
        "upper_bound",
        "actual",
        "absolute_error",
        "percentage_error",
        "signed_error",
    )
    @classmethod
    def require_finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("evaluation values must be finite")
        return None if value is None else value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_consistency(self) -> "ForecastEvaluationRow":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if self.training_cutoff is not None and self.training_cutoff > self.prediction_as_of:
            raise ValueError("training_cutoff cannot be after prediction_as_of")
        if self.status is EvaluationStatus.EVALUATED:
            required = (
                self.forecast_id,
                self.prediction,
                self.actual,
                self.absolute_error,
                self.signed_error,
                self.interval_hit,
                self.demand_band,
            )
            if any(value is None for value in required):
                raise ValueError("evaluated rows require forecast, actual, errors, and band")
        elif any(
            value is not None
            for value in (
                self.actual,
                self.absolute_error,
                self.percentage_error,
                self.signed_error,
                self.interval_hit,
            )
        ):
            raise ValueError("censored or abstained rows cannot carry scored actuals")
        if self.prediction is not None and self.prediction < 0:
            raise ValueError("prediction cannot be negative")
        if self.actual is not None and self.actual < 0:
            raise ValueError("actual cannot be negative")
        if self.lower_bound is not None and self.upper_bound is not None:
            if self.lower_bound > self.upper_bound:
                raise ValueError("lower_bound cannot exceed upper_bound")
        return self


class ForecastMetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_kind: ForecastModelKind
    evaluated_count: Annotated[int, Field(ge=0)]
    censored_count: Annotated[int, Field(ge=0)]
    abstention_count: Annotated[int, Field(ge=0)]
    mae: Decimal | None
    rmse: Decimal | None
    wmape: Decimal | None
    bias: Decimal | None
    interval_coverage: Decimal | None
    mean_interval_width: Decimal | None

    @field_validator(
        "mae", "rmse", "wmape", "bias", "interval_coverage", "mean_interval_width"
    )
    @classmethod
    def require_finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("summary metrics must be finite")
        return None if value is None else value.quantize(_DP, rounding=ROUND_HALF_UP)


class SubgroupComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: Identifier
    value: Identifier
    baseline: ForecastMetricSummary
    model: ForecastMetricSummary
    relative_wmape_regression: Decimal | None
    exceeds_limit: bool


class ModelAcceptanceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AcceptanceStatus
    primary_metric: str = "WMAPE"
    baseline_wmape: Decimal | None
    model_wmape: Decimal | None
    relative_improvement: Decimal | None
    required_improvement: Decimal
    max_subgroup_regression: Decimal
    failing_subgroups: tuple[Identifier, ...]
    reasons: tuple[str, ...]


class ForecastEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: Identifier
    evaluation_version: Identifier
    split_strategy: Identifier
    rows: tuple[ForecastEvaluationRow, ...]
    baseline_summary: ForecastMetricSummary
    model_summary: ForecastMetricSummary
    subgroup_comparisons: tuple[SubgroupComparison, ...]
    acceptance: ModelAcceptanceDecision


def demand_band(actual: Decimal) -> DemandBand:
    if actual == 0:
        return DemandBand.ZERO
    if actual <= 10:
        return DemandBand.LOW
    if actual <= 50:
        return DemandBand.MEDIUM
    return DemandBand.HIGH


def compute_metric_summary(
    rows: Sequence[ForecastEvaluationRow], model_kind: ForecastModelKind
) -> ForecastMetricSummary:
    selected = [row for row in rows if row.model_kind is model_kind]
    evaluated = [row for row in selected if row.status is EvaluationStatus.EVALUATED]
    censored = sum(row.status is EvaluationStatus.CENSORED for row in selected)
    abstained = sum(row.status is EvaluationStatus.ABSTAINED for row in selected)
    if not evaluated:
        return ForecastMetricSummary(
            model_kind=model_kind,
            evaluated_count=0,
            censored_count=censored,
            abstention_count=abstained,
            mae=None,
            rmse=None,
            wmape=None,
            bias=None,
            interval_coverage=None,
            mean_interval_width=None,
        )

    count = Decimal(len(evaluated))
    absolute = [row.absolute_error for row in evaluated if row.absolute_error is not None]
    signed = [row.signed_error for row in evaluated if row.signed_error is not None]
    actuals = [row.actual for row in evaluated if row.actual is not None]
    squared = [error * error for error in signed]
    mae = sum(absolute, Decimal("0")) / count
    rmse = Decimal(str(sqrt(float(sum(squared, Decimal("0")) / count))))
    total_actual = sum(actuals, Decimal("0"))
    wmape = None if total_actual == 0 else sum(absolute, Decimal("0")) / total_actual
    bias = sum(signed, Decimal("0")) / count
    hits = [row.interval_hit for row in evaluated if row.interval_hit is not None]
    coverage = Decimal(sum(bool(item) for item in hits)) / Decimal(len(hits))
    widths = [
        row.upper_bound - row.lower_bound
        for row in evaluated
        if row.upper_bound is not None and row.lower_bound is not None
    ]
    mean_width = sum(widths, Decimal("0")) / Decimal(len(widths)) if widths else None
    return ForecastMetricSummary(
        model_kind=model_kind,
        evaluated_count=len(evaluated),
        censored_count=censored,
        abstention_count=abstained,
        mae=mae,
        rmse=rmse,
        wmape=wmape,
        bias=bias,
        interval_coverage=coverage,
        mean_interval_width=mean_width,
    )


def _relative_regression(
    baseline: ForecastMetricSummary, model: ForecastMetricSummary
) -> Decimal | None:
    if baseline.wmape is None or model.wmape is None:
        return None
    if baseline.wmape == 0:
        return Decimal("0") if model.wmape == 0 else Decimal("Infinity")
    return ((model.wmape - baseline.wmape) / baseline.wmape).quantize(
        _DP, rounding=ROUND_HALF_UP
    )


def compare_subgroups(
    rows: Sequence[ForecastEvaluationRow],
) -> tuple[SubgroupComparison, ...]:
    dimensions = {
        "outlet_id": lambda row: row.outlet_id,
        "sku_id": lambda row: row.sku_id,
        "service_window": lambda row: row.service_window,
        "demand_band": lambda row: row.demand_band.value if row.demand_band else None,
    }
    results: list[SubgroupComparison] = []
    for dimension, getter in dimensions.items():
        values = sorted({value for row in rows if (value := getter(row)) is not None})
        for value in values:
            group = [row for row in rows if getter(row) == value]
            baseline = compute_metric_summary(group, ForecastModelKind.BASELINE)
            model = compute_metric_summary(group, ForecastModelKind.GBT)
            regression = _relative_regression(baseline, model)
            exceeds = regression is not None and (
                not regression.is_finite() or regression > MAX_SUBGROUP_REGRESSION
            )
            results.append(
                SubgroupComparison(
                    dimension=dimension,
                    value=value,
                    baseline=baseline,
                    model=model,
                    relative_wmape_regression=regression if regression is None or regression.is_finite() else None,
                    exceeds_limit=exceeds,
                )
            )
    return tuple(results)


def assess_model_acceptance(
    baseline: ForecastMetricSummary,
    model: ForecastMetricSummary,
    subgroups: Sequence[SubgroupComparison],
    *,
    required_improvement: Decimal = PRIMARY_IMPROVEMENT_REQUIRED,
    max_subgroup_regression: Decimal = MAX_SUBGROUP_REGRESSION,
) -> ModelAcceptanceDecision:
    if required_improvement < 0 or max_subgroup_regression < 0:
        raise ValueError("acceptance thresholds cannot be negative")
    if (
        baseline.wmape is None
        or model.wmape is None
        or baseline.evaluated_count == 0
        or model.evaluated_count == 0
        or baseline.evaluated_count != model.evaluated_count
    ):
        return ModelAcceptanceDecision(
            status=AcceptanceStatus.INSUFFICIENT_EVIDENCE,
            baseline_wmape=baseline.wmape,
            model_wmape=model.wmape,
            relative_improvement=None,
            required_improvement=required_improvement,
            max_subgroup_regression=max_subgroup_regression,
            failing_subgroups=(),
            reasons=(
                "baseline and model require paired, non-empty, non-zero-denominator WMAPE",
            ),
        )

    if baseline.wmape == 0:
        improvement = Decimal("0") if model.wmape == 0 else Decimal("-1")
    else:
        improvement = ((baseline.wmape - model.wmape) / baseline.wmape).quantize(
            _DP, rounding=ROUND_HALF_UP
        )
    failing = tuple(
        f"{item.dimension}={item.value}"
        for item in subgroups
        if (
            item.relative_wmape_regression is not None
            and item.relative_wmape_regression > max_subgroup_regression
        )
        or (
            item.relative_wmape_regression is None
            and item.exceeds_limit
        )
    )
    reasons: list[str] = []
    if improvement < required_improvement:
        reasons.append("model did not meet required relative WMAPE improvement")
    if failing:
        reasons.append("model exceeded the subgroup WMAPE regression limit")
    return ModelAcceptanceDecision(
        status=AcceptanceStatus.ACCEPTED if not reasons else AcceptanceStatus.REJECTED,
        baseline_wmape=baseline.wmape,
        model_wmape=model.wmape,
        relative_improvement=improvement,
        required_improvement=required_improvement,
        max_subgroup_regression=max_subgroup_regression,
        failing_subgroups=failing,
        reasons=tuple(reasons),
    )


def compute_report_id(rows: Sequence[ForecastEvaluationRow]) -> str:
    payload = [row.model_dump(mode="json") for row in rows]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"eval_{sha256(encoded).hexdigest()[:24]}"
