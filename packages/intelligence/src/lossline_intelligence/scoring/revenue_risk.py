"""Estimated revenue-at-risk calculator.

Formula (FINAL_IMPLEMENTATION_PLAN.md):
  observed_cancelled_value  = sum(cancelled order amounts in incident window)
  excess_cancel_rate        = max(0, current_cancel_rate - baseline_cancel_rate)
  projected_revenue_at_risk = order_rate_per_minute
                              * forecast_horizon_minutes
                              * avg_order_value
                              * excess_cancel_rate
  display_total_exposure    = observed_cancelled_value + projected_revenue_at_risk

Label result "Estimated revenue exposure" — NOT "profit loss" or "causal certainty".
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

FORECAST_HORIZON_MINUTES: int = 60
FORMULA_VERSION: str = "revenue_v1"
EXPOSURE_LABEL: str = "Estimated revenue exposure"


class RevenueStatus(StrEnum):
    OK = "OK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class RevenueInputs:
    observed_cancelled_value: Decimal
    current_cancel_rate: float
    baseline_cancel_rate: float
    current_order_rate_per_min: float
    avg_order_value: Decimal
    currency: str
    forecast_horizon_minutes: int = FORECAST_HORIZON_MINUTES


@dataclass(frozen=True)
class RevenueResult:
    status: RevenueStatus
    observed_cancelled_value: Decimal
    projected_revenue_at_risk: Decimal
    display_total_exposure: Decimal
    excess_cancel_rate: float
    currency: str
    formula_version: str
    exposure_label: str = EXPOSURE_LABEL
    reason: str = ""


_ZERO = Decimal("0")


def estimate_revenue_at_risk(inputs: RevenueInputs) -> RevenueResult:
    """Compute estimated revenue exposure for a cancellation episode."""
    insufficient = _check_inputs(inputs)
    if insufficient:
        return RevenueResult(
            status=RevenueStatus.INSUFFICIENT_DATA,
            observed_cancelled_value=_ZERO,
            projected_revenue_at_risk=_ZERO,
            display_total_exposure=_ZERO,
            excess_cancel_rate=0.0,
            currency=inputs.currency or "UNKNOWN",
            formula_version=FORMULA_VERSION,
            reason=insufficient,
        )

    excess_rate = max(0.0, inputs.current_cancel_rate - inputs.baseline_cancel_rate)
    projected = (
        Decimal(str(inputs.current_order_rate_per_min))
        * Decimal(str(inputs.forecast_horizon_minutes))
        * inputs.avg_order_value
        * Decimal(str(excess_rate))
    )
    total = inputs.observed_cancelled_value + projected

    return RevenueResult(
        status=RevenueStatus.OK,
        observed_cancelled_value=inputs.observed_cancelled_value,
        projected_revenue_at_risk=projected,
        display_total_exposure=total,
        excess_cancel_rate=round(excess_rate, 6),
        currency=inputs.currency,
        formula_version=FORMULA_VERSION,
    )


def _check_inputs(inputs: RevenueInputs) -> str:
    if not inputs.currency or not inputs.currency.strip():
        return "currency is missing"
    if inputs.avg_order_value <= _ZERO:
        return "avg_order_value must be positive"
    if inputs.current_order_rate_per_min < 0:
        return "current_order_rate_per_min cannot be negative"
    if not inputs.observed_cancelled_value.is_finite():
        return "observed_cancelled_value is not finite"
    if not inputs.avg_order_value.is_finite():
        return "avg_order_value is not finite"
    return ""
