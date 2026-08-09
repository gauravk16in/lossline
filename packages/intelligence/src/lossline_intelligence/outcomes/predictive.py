"""Pure C21 outcome maturity, forecast verification and risk evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from hashlib import sha256
import json
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OUTCOME_RULE_VERSION = "predictive_outcome.v1"
DEFAULT_MATURITY_DELAY_MINUTES = 30
_DP = Decimal("0.0001")


class ActualOutcomeStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    CENSORED = "CENSORED"
    MISSING = "MISSING"


class OutcomeAbstentionReason(StrEnum):
    NOT_MATURE = "NOT_MATURE"


@dataclass(frozen=True)
class OutcomeAbstention:
    forecast_id: str
    reason: OutcomeAbstentionReason
    matures_at: datetime


class ActualOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    outcome_id: Identifier
    forecast_id: Identifier
    outlet_id: Identifier
    sku_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    actual_demand: Decimal | None
    fulfilled_quantity: Decimal | None
    unfulfilled_quantity: Decimal | None
    ending_inventory: Decimal | None
    capacity_utilization: Decimal | None
    status: ActualOutcomeStatus
    source_ids: tuple[Identifier, ...]
    matured_at: datetime
    rule_version: Identifier

    @field_validator("window_start", "window_end", "matured_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None: raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("actual_demand", "fulfilled_quantity", "unfulfilled_quantity", "ending_inventory", "capacity_utilization")
    @classmethod
    def finite(cls, value: Decimal | None) -> Decimal | None:
        if value is None: return None
        if not value.is_finite(): raise ValueError("outcome metrics must be finite")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def consistent(self) -> "ActualOutcome":
        if self.window_end <= self.window_start: raise ValueError("window_end must be after window_start")
        if len(set(self.source_ids)) != len(self.source_ids): raise ValueError("source_ids must be unique")
        metrics = (self.actual_demand, self.fulfilled_quantity, self.unfulfilled_quantity)
        if self.status is ActualOutcomeStatus.MISSING and any(value is not None for value in metrics):
            raise ValueError("missing outcome cannot carry demand quantities")
        if self.status is not ActualOutcomeStatus.MISSING and any(value is None for value in metrics):
            raise ValueError("available/censored outcome requires demand quantities")
        if self.status is not ActualOutcomeStatus.MISSING:
            assert self.actual_demand is not None and self.fulfilled_quantity is not None and self.unfulfilled_quantity is not None
            if min(self.actual_demand, self.fulfilled_quantity, self.unfulfilled_quantity) < 0:
                raise ValueError("demand quantities must be non-negative")
            if self.fulfilled_quantity + self.unfulfilled_quantity != self.actual_demand:
                raise ValueError("fulfilled plus unfulfilled must equal actual demand")
        if self.capacity_utilization is not None and self.capacity_utilization < 0:
            raise ValueError("capacity utilization must be non-negative")
        return self


class ForecastLike(Protocol):
    forecast_id: str; outlet_id: str; sku_id: str; service_window: str
    window_start: datetime; window_end: datetime
    point_demand: Decimal; lower_demand: Decimal; upper_demand: Decimal


@dataclass(frozen=True)
class ForecastOutcomeEvaluation:
    forecast_id: str
    outcome_id: str
    absolute_error: Decimal
    signed_error: Decimal
    interval_hit: bool
    shortage_occurred: bool
    rule_version: str


@dataclass(frozen=True)
class DecisionOutcomeEvaluation:
    decision_id: str
    outcome_id: str
    manager_decision: str
    observed_status: ActualOutcomeStatus
    observed_shortage: bool | None
    association_note: str
    rule_version: str


@dataclass(frozen=True)
class RiskEvaluation:
    sample_count: int
    true_positive: int; false_positive: int; true_negative: int; false_negative: int
    precision: Decimal | None; recall: Decimal | None; f1: Decimal | None


def mature_actual_outcome(*, forecast: ForecastLike, now: datetime,
    actual_demand: Decimal | None, fulfilled_quantity: Decimal | None,
    unfulfilled_quantity: Decimal | None, ending_inventory: Decimal | None,
    capacity_utilization: Decimal | None, status: ActualOutcomeStatus,
    source_ids: tuple[str, ...], maturity_delay_minutes: int = DEFAULT_MATURITY_DELAY_MINUTES,
    rule_version: str = OUTCOME_RULE_VERSION) -> ActualOutcome | OutcomeAbstention:
    if now.tzinfo is None or now.utcoffset() is None: raise ValueError("now must be timezone-aware")
    if maturity_delay_minutes < 0: raise ValueError("maturity delay must be non-negative")
    matures_at = forecast.window_end + timedelta(minutes=maturity_delay_minutes)
    if now < matures_at: return OutcomeAbstention(forecast.forecast_id, OutcomeAbstentionReason.NOT_MATURE, matures_at)
    payload = {"forecast": forecast.forecast_id, "status": status.value, "actual": str(actual_demand),
        "fulfilled": str(fulfilled_quantity), "unfulfilled": str(unfulfilled_quantity),
        "ending": str(ending_inventory), "capacity": str(capacity_utilization),
        "sources": source_ids, "rule": rule_version}
    tag = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return ActualOutcome(outcome_id=f"out_{tag}", forecast_id=forecast.forecast_id,
        outlet_id=forecast.outlet_id, sku_id=forecast.sku_id, service_window=forecast.service_window,
        window_start=forecast.window_start, window_end=forecast.window_end,
        actual_demand=actual_demand, fulfilled_quantity=fulfilled_quantity,
        unfulfilled_quantity=unfulfilled_quantity, ending_inventory=ending_inventory,
        capacity_utilization=capacity_utilization, status=status, source_ids=source_ids,
        matured_at=matures_at, rule_version=rule_version)


def evaluate_forecast_outcome(forecast: ForecastLike, outcome: ActualOutcome) -> ForecastOutcomeEvaluation | None:
    if (forecast.forecast_id, forecast.outlet_id, forecast.sku_id, forecast.service_window,
        forecast.window_start, forecast.window_end) != (outcome.forecast_id, outcome.outlet_id,
        outcome.sku_id, outcome.service_window, outcome.window_start, outcome.window_end):
        raise ValueError("forecast and outcome grain/window must match")
    if outcome.status is not ActualOutcomeStatus.AVAILABLE: return None
    assert outcome.actual_demand is not None and outcome.unfulfilled_quantity is not None
    signed = (forecast.point_demand - outcome.actual_demand).quantize(_DP)
    return ForecastOutcomeEvaluation(forecast.forecast_id, outcome.outcome_id, abs(signed), signed,
        forecast.lower_demand <= outcome.actual_demand <= forecast.upper_demand,
        outcome.unfulfilled_quantity > 0, OUTCOME_RULE_VERSION)


def evaluate_decision_outcome(*, decision_id: str, manager_decision: str,
    outcome: ActualOutcome) -> DecisionOutcomeEvaluation:
    shortage = None if outcome.unfulfilled_quantity is None else outcome.unfulfilled_quantity > 0
    return DecisionOutcomeEvaluation(decision_id, outcome.outcome_id, manager_decision,
        outcome.status, shortage,
        "Observed after the manager decision; this record does not establish causation.", OUTCOME_RULE_VERSION)


def evaluate_risk_predictions(pairs: tuple[tuple[bool, bool], ...]) -> RiskEvaluation:
    tp = sum(predicted and actual for predicted, actual in pairs)
    fp = sum(predicted and not actual for predicted, actual in pairs)
    tn = sum(not predicted and not actual for predicted, actual in pairs)
    fn = sum(not predicted and actual for predicted, actual in pairs)
    precision = None if tp + fp == 0 else (Decimal(tp) / Decimal(tp + fp)).quantize(_DP)
    recall = None if tp + fn == 0 else (Decimal(tp) / Decimal(tp + fn)).quantize(_DP)
    f1 = None if precision is None or recall is None or precision + recall == 0 else (Decimal("2") * precision * recall / (precision + recall)).quantize(_DP)
    return RiskEvaluation(len(pairs), tp, fp, tn, fn, precision, recall, f1)
