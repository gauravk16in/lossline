"""Conservative deterministic estimated revenue-exposure calculation.

Currency values are derived only from explicit evidence inputs. This module
does not infer outlet revenue and has no LLM integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


FORECAST_HORIZON_MINUTES: int = 60
FORMULA_VERSION: str = "revenue_risk.v2"
EXPOSURE_LABEL: str = "Estimated revenue exposure"
_ZERO = Decimal("0")
_CURRENCY_QUANTUM = Decimal("0.01")


class RevenueStatus(StrEnum):
    OK = "OK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class RevenueInputs:
    """Explicit evidence and configuration used by the estimate.

    ``avg_order_value`` must come from known same-currency order evidence. It
    may be ``None`` to represent missing evidence; the estimator then returns
    ``INSUFFICIENT_DATA`` instead of fabricating a value.
    """

    observed_cancelled_value: Decimal | None
    current_cancel_rate: Decimal | float | None
    baseline_cancel_rate: Decimal | float | None
    current_order_rate_per_min: Decimal | float | None
    avg_order_value: Decimal | None
    currency: str | None
    forecast_horizon_minutes: int = FORECAST_HORIZON_MINUTES


@dataclass(frozen=True)
class RevenueRiskEstimate:
    """Available estimate or an explicit insufficient-data result."""

    status: RevenueStatus
    estimated_amount: Decimal | None
    currency: str | None
    assumptions: tuple[str, ...]
    components: Mapping[str, Decimal | int | str | None]
    formula_version: str
    is_estimate: bool = True
    reason: str = ""
    exposure_label: str = EXPOSURE_LABEL

    # Compatibility accessors for existing callers.
    @property
    def observed_cancelled_value(self) -> Decimal:
        value = self.components.get("observed_cancelled_value")
        return value if isinstance(value, Decimal) else _ZERO

    @property
    def projected_revenue_at_risk(self) -> Decimal:
        value = self.components.get("projected_revenue_at_risk")
        return value if isinstance(value, Decimal) else _ZERO

    @property
    def display_total_exposure(self) -> Decimal | None:
        return self.estimated_amount

    @property
    def excess_cancel_rate(self) -> float:
        value = self.components.get("excess_cancel_rate")
        return float(value) if isinstance(value, Decimal) else 0.0


# Compatibility name used by the existing pipeline exports.
RevenueResult = RevenueRiskEstimate


def estimate_revenue_at_risk(inputs: RevenueInputs) -> RevenueRiskEstimate:
    """Estimate exposure from explicit cancellation and order evidence.

    Formula::

        excess_cancel_rate = max(0, current_rate - baseline_rate)
        projected_orders = order_rate_per_minute * continuation_horizon_minutes
        projected_excess_cancellations = projected_orders * excess_cancel_rate
        projected_exposure = projected_excess_cancellations * average_order_value
        estimated_amount = observed_cancelled_value + projected_exposure

    The final currency amount is rounded down to two decimal places so the demo
    does not overstate exposure through rounding.
    """
    normalized, reason = _normalize_inputs(inputs)
    if reason:
        return _unavailable(inputs.currency, reason)

    assert normalized is not None
    observed, current_rate, baseline_rate, order_rate, aov = normalized
    excess_rate = max(_ZERO, current_rate - baseline_rate)
    horizon = Decimal(inputs.forecast_horizon_minutes)
    projected_orders = order_rate * horizon
    projected_excess_cancellations = projected_orders * excess_rate
    projected_exposure = projected_excess_cancellations * aov
    estimated_amount = (observed + projected_exposure).quantize(
        _CURRENCY_QUANTUM,
        rounding=ROUND_DOWN,
    )

    components: Mapping[str, Decimal | int | str | None] = MappingProxyType(
        {
            "observed_cancelled_value": observed,
            "current_cancel_rate": current_rate,
            "baseline_cancel_rate": baseline_rate,
            "excess_cancel_rate": excess_rate,
            "current_order_rate_per_min": order_rate,
            "forecast_horizon_minutes": inputs.forecast_horizon_minutes,
            "projected_orders": projected_orders,
            "projected_excess_cancellations": projected_excess_cancellations,
            "avg_order_value": aov,
            "projected_revenue_at_risk": projected_exposure,
        }
    )
    assumptions = (
        "Average order value is supplied by same-currency order evidence.",
        "Current order rate continues only for the configured forecast horizon.",
        "Excess cancellation rate is current rate minus baseline, floored at zero.",
        "The result is estimated revenue exposure, not observed profit loss.",
    )

    return RevenueRiskEstimate(
        status=RevenueStatus.OK,
        estimated_amount=estimated_amount,
        currency=inputs.currency.strip() if inputs.currency else None,
        assumptions=assumptions,
        components=components,
        formula_version=FORMULA_VERSION,
    )


def _to_decimal(value: Decimal | float | None, field_name: str) -> tuple[Decimal | None, str]:
    if value is None:
        return None, f"{field_name} is missing"
    converted = value if isinstance(value, Decimal) else Decimal(str(value))
    if not converted.is_finite():
        return None, f"{field_name} must be finite"
    return converted, ""


def _normalize_inputs(
    inputs: RevenueInputs,
) -> tuple[tuple[Decimal, Decimal, Decimal, Decimal, Decimal] | None, str]:
    if not inputs.currency or not inputs.currency.strip():
        return None, "currency is missing"
    if inputs.forecast_horizon_minutes <= 0:
        return None, "forecast_horizon_minutes must be positive"

    observed, reason = _to_decimal(
        inputs.observed_cancelled_value,
        "observed_cancelled_value",
    )
    if reason:
        return None, reason
    current, reason = _to_decimal(inputs.current_cancel_rate, "current_cancel_rate")
    if reason:
        return None, reason
    baseline, reason = _to_decimal(inputs.baseline_cancel_rate, "baseline_cancel_rate")
    if reason:
        return None, reason
    order_rate, reason = _to_decimal(
        inputs.current_order_rate_per_min,
        "current_order_rate_per_min",
    )
    if reason:
        return None, reason
    aov, reason = _to_decimal(inputs.avg_order_value, "avg_order_value")
    if reason:
        return None, reason

    assert observed is not None
    assert current is not None
    assert baseline is not None
    assert order_rate is not None
    assert aov is not None

    if observed < _ZERO:
        return None, "observed_cancelled_value cannot be negative"
    if not _ZERO <= current <= Decimal("1"):
        return None, "current_cancel_rate must be between 0 and 1"
    if not _ZERO <= baseline <= Decimal("1"):
        return None, "baseline_cancel_rate must be between 0 and 1"
    if order_rate < _ZERO:
        return None, "current_order_rate_per_min cannot be negative"
    if aov <= _ZERO:
        return None, "avg_order_value must be positive"

    return (observed, current, baseline, order_rate, aov), ""


def _unavailable(currency: str | None, reason: str) -> RevenueRiskEstimate:
    return RevenueRiskEstimate(
        status=RevenueStatus.INSUFFICIENT_DATA,
        estimated_amount=None,
        currency=currency.strip() if currency and currency.strip() else None,
        assumptions=(),
        components=MappingProxyType({}),
        formula_version=FORMULA_VERSION,
        reason=reason,
    )
