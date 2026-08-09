"""Comparable-history demand baseline and rolling evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from hashlib import sha256
import json
from math import sqrt
from statistics import median
from typing import Annotated, Mapping, Sequence

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from lossline_intelligence.features.snapshot import DatasetRow, FeatureSnapshot


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

BASELINE_VERSION = "comparable_median.v1"
INTERVAL_METHOD = "empirical_comparable_demand_80.v1"
MIN_HISTORY: int = 4
_DP = Decimal("0.0001")


class BaselineScope(StrEnum):
    OUTLET_SKU_WEEKDAY_WINDOW = "OUTLET_SKU_WEEKDAY_WINDOW"
    SKU_WEEKDAY_WINDOW = "SKU_WEEKDAY_WINDOW"
    OUTLET_SKU_WINDOW = "OUTLET_SKU_WINDOW"
    SKU_WINDOW = "SKU_WINDOW"
    OUTLET_CATEGORY_WEEKDAY_WINDOW = "OUTLET_CATEGORY_WEEKDAY_WINDOW"
    CATEGORY_WEEKDAY_WINDOW = "CATEGORY_WEEKDAY_WINDOW"
    GLOBAL_WEEKDAY_WINDOW = "GLOBAL_WEEKDAY_WINDOW"
    GLOBAL = "GLOBAL"


class BaselineAbstentionReason(StrEnum):
    INSUFFICIENT_UNCENSORED_HISTORY = "INSUFFICIENT_UNCENSORED_HISTORY"
    INVALID_TARGET_SNAPSHOT = "INVALID_TARGET_SNAPSHOT"


class BaselineForecast(BaseModel):
    """Validated baseline forecast at the canonical predictive grain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    forecast_id: Identifier
    forecast_version: Identifier
    interval_method: Identifier
    prediction_as_of: datetime
    outlet_id: Identifier
    sku_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    feature_snapshot_id: Identifier
    point_demand: Decimal
    lower_demand: Decimal
    upper_demand: Decimal
    scope: BaselineScope
    sample_count: Annotated[int, Field(ge=1)]
    source_snapshot_ids: tuple[Identifier, ...]
    data_sufficient: bool

    @field_validator("prediction_as_of", "window_start", "window_end")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(timezone.utc)

    @field_validator("point_demand", "lower_demand", "upper_demand")
    @classmethod
    def validate_demand(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("forecast demand must be finite and non-negative")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @field_validator("source_snapshot_ids")
    @classmethod
    def validate_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source snapshot IDs must be unique")
        return value

    @model_validator(mode="after")
    def validate_ranges(self) -> "BaselineForecast":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if not self.lower_demand <= self.point_demand <= self.upper_demand:
            raise ValueError("forecast bounds must contain point_demand")
        if self.sample_count != len(self.source_snapshot_ids):
            raise ValueError("sample_count must match source_snapshot_ids")
        return self


@dataclass(frozen=True)
class BaselineAbstention:
    feature_snapshot_id: str
    reason: BaselineAbstentionReason
    available_uncensored_history: int
    minimum_history: int


@dataclass(frozen=True)
class BaselineMetrics:
    forecast_count: int
    abstention_count: int
    mae: Decimal | None
    rmse: Decimal | None
    wmape: Decimal | None
    bias: Decimal | None


def _weekday(snapshot: FeatureSnapshot) -> int | None:
    value = snapshot.feature_values.get("context.weekday")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("prediction_as_of must include a UTC offset")
    return value.astimezone(timezone.utc)


def _eligible_history(
    rows: Sequence[DatasetRow], target: FeatureSnapshot, as_of: datetime
) -> tuple[DatasetRow, ...]:
    eligible = [
        row
        for row in rows
        if not row.censored
        and row.target_demand_quantity >= 0
        and row.snapshot.window_end <= as_of
        and row.snapshot.window_start < target.window_start
    ]
    return tuple(
        sorted(
            eligible,
            key=lambda row: (
                row.snapshot.window_start,
                row.snapshot.outlet_id,
                row.snapshot.sku_id,
                row.snapshot.snapshot_id,
            ),
        )
    )


def _matches(
    row: DatasetRow,
    target: FeatureSnapshot,
    scope: BaselineScope,
    sku_categories: Mapping[str, str],
) -> bool:
    source = row.snapshot
    same_weekday = _weekday(source) == _weekday(target)
    same_window = source.service_window == target.service_window
    target_category = sku_categories.get(target.sku_id)
    source_category = sku_categories.get(source.sku_id)

    if scope is BaselineScope.OUTLET_SKU_WEEKDAY_WINDOW:
        return (
            source.outlet_id == target.outlet_id
            and source.sku_id == target.sku_id
            and same_weekday
            and same_window
        )
    if scope is BaselineScope.SKU_WEEKDAY_WINDOW:
        return source.sku_id == target.sku_id and same_weekday and same_window
    if scope is BaselineScope.OUTLET_SKU_WINDOW:
        return (
            source.outlet_id == target.outlet_id
            and source.sku_id == target.sku_id
            and same_window
        )
    if scope is BaselineScope.SKU_WINDOW:
        return source.sku_id == target.sku_id and same_window
    if scope is BaselineScope.OUTLET_CATEGORY_WEEKDAY_WINDOW:
        return (
            target_category is not None
            and source_category == target_category
            and source.outlet_id == target.outlet_id
            and same_weekday
            and same_window
        )
    if scope is BaselineScope.CATEGORY_WEEKDAY_WINDOW:
        return (
            target_category is not None
            and source_category == target_category
            and same_weekday
            and same_window
        )
    if scope is BaselineScope.GLOBAL_WEEKDAY_WINDOW:
        return same_weekday and same_window
    return True


def _quantile(values: Sequence[Decimal], probability: Decimal) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires at least one value")
    position = probability * Decimal(len(ordered) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - Decimal(lower_index)
    result = ordered[lower_index] + fraction * (
        ordered[upper_index] - ordered[lower_index]
    )
    return result.quantize(_DP, rounding=ROUND_HALF_UP)


def _forecast_id(target: FeatureSnapshot, as_of: datetime) -> str:
    payload = json.dumps(
        {
            "as_of": as_of.isoformat(),
            "snapshot_id": target.snapshot_id,
            "version": BASELINE_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"fcst_baseline_{sha256(payload).hexdigest()[:20]}"


def forecast_baseline(
    target: FeatureSnapshot,
    history: Sequence[DatasetRow],
    *,
    prediction_as_of: datetime,
    sku_categories: Mapping[str, str] | None = None,
    min_history: int = MIN_HISTORY,
) -> BaselineForecast | BaselineAbstention:
    """Forecast demand from the first sufficiently populated comparison scope."""

    if min_history < 1:
        raise ValueError("min_history must be positive")
    as_of = _utc(prediction_as_of)
    if target.window_start < as_of:
        return BaselineAbstention(
            feature_snapshot_id=target.snapshot_id,
            reason=BaselineAbstentionReason.INVALID_TARGET_SNAPSHOT,
            available_uncensored_history=0,
            minimum_history=min_history,
        )

    categories = sku_categories or {}
    eligible = _eligible_history(history, target, as_of)
    scopes = tuple(BaselineScope)
    chosen_scope: BaselineScope | None = None
    chosen: tuple[DatasetRow, ...] = ()
    for scope in scopes:
        candidates = tuple(
            row for row in eligible if _matches(row, target, scope, categories)
        )
        if len(candidates) >= min_history:
            chosen_scope = scope
            chosen = candidates
            break

    if chosen_scope is None:
        return BaselineAbstention(
            feature_snapshot_id=target.snapshot_id,
            reason=BaselineAbstentionReason.INSUFFICIENT_UNCENSORED_HISTORY,
            available_uncensored_history=len(eligible),
            minimum_history=min_history,
        )

    demands = tuple(Decimal(row.target_demand_quantity) for row in chosen)
    point = Decimal(median(demands)).quantize(_DP, rounding=ROUND_HALF_UP)
    lower = min(point, _quantile(demands, Decimal("0.10")))
    upper = max(point, _quantile(demands, Decimal("0.90")))
    return BaselineForecast(
        forecast_id=_forecast_id(target, as_of),
        forecast_version=BASELINE_VERSION,
        interval_method=INTERVAL_METHOD,
        prediction_as_of=as_of,
        outlet_id=target.outlet_id,
        sku_id=target.sku_id,
        service_window=target.service_window,
        window_start=target.window_start,
        window_end=target.window_end,
        feature_snapshot_id=target.snapshot_id,
        point_demand=point,
        lower_demand=lower,
        upper_demand=upper,
        scope=chosen_scope,
        sample_count=len(chosen),
        source_snapshot_ids=tuple(row.snapshot.snapshot_id for row in chosen),
        data_sufficient=True,
    )


def evaluate_rolling_baseline(
    rows: Sequence[DatasetRow],
    *,
    sku_categories: Mapping[str, str] | None = None,
    min_history: int = MIN_HISTORY,
) -> BaselineMetrics:
    """Evaluate forecasts using only rows strictly earlier than each target."""

    ordered = sorted(
        rows,
        key=lambda row: (
            row.snapshot.window_start,
            row.snapshot.outlet_id,
            row.snapshot.sku_id,
        ),
    )
    errors: list[Decimal] = []
    actuals: list[Decimal] = []
    abstentions = 0
    for index, row in enumerate(ordered):
        if row.censored:
            continue
        result = forecast_baseline(
            row.snapshot,
            ordered[:index],
            prediction_as_of=row.snapshot.window_start,
            sku_categories=sku_categories,
            min_history=min_history,
        )
        if isinstance(result, BaselineAbstention):
            abstentions += 1
            continue
        actual = Decimal(row.target_demand_quantity)
        errors.append(result.point_demand - actual)
        actuals.append(actual)

    if not errors:
        return BaselineMetrics(0, abstentions, None, None, None, None)
    count = Decimal(len(errors))
    absolute = [abs(error) for error in errors]
    mae = (sum(absolute, Decimal("0")) / count).quantize(
        _DP, rounding=ROUND_HALF_UP
    )
    mean_squared = sum((error * error for error in errors), Decimal("0")) / count
    rmse = Decimal(str(sqrt(float(mean_squared)))).quantize(
        _DP, rounding=ROUND_HALF_UP
    )
    total_actual = sum(actuals, Decimal("0"))
    wmape = (
        None
        if total_actual == 0
        else (sum(absolute, Decimal("0")) / total_actual).quantize(
            _DP, rounding=ROUND_HALF_UP
        )
    )
    bias = (sum(errors, Decimal("0")) / count).quantize(
        _DP, rounding=ROUND_HALF_UP
    )
    return BaselineMetrics(len(errors), abstentions, mae, rmse, wmape, bias)
