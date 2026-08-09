"""Deterministic inventory projection engine.

``project_inventory`` takes a ``ForecastResult`` and current supply
inputs, applies safety-buffer and replenishment arithmetic, and returns
an immutable ``InventoryProjection``.

All formula constants are module-level, never hardcoded in logic.
Callers may override any threshold as a keyword argument.
"""

from __future__ import annotations

import math
from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json

from lossline_intelligence.forecasting import ForecastLike
from lossline_intelligence.inventory.projection import (
    InventoryProjection,
    ShortageSeverity,
    StockoutTimingMethod,
)

# ---------------------------------------------------------------------------
# Rule version — every projection carries this for traceability
# ---------------------------------------------------------------------------

RULE_VERSION = "inventory.v1"

# ---------------------------------------------------------------------------
# Default thresholds (module-level constants, overridable by caller)
# ---------------------------------------------------------------------------

DEFAULT_SAFETY_BUFFER_PCT: Decimal = Decimal("0.10")
DEFAULT_MIN_SAFETY_BUFFER: int = 2
DEFAULT_SURPLUS_RISK_MULTIPLIER: Decimal = Decimal("2.0")

# Shortage severity thresholds (shortage / demand_point ratio)
_SEVERITY_LOW: Decimal = Decimal("0.10")
_SEVERITY_MEDIUM: Decimal = Decimal("0.25")
_SEVERITY_HIGH: Decimal = Decimal("0.50")

_DP = Decimal("0.0001")
_ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_safety_buffer(
    opening_inventory: int,
    safety_buffer_pct: Decimal,
    min_safety_buffer: int,
) -> int:
    """Compute safety buffer as max(min, ceil(opening × pct))."""
    pct_buffer = math.ceil(opening_inventory * float(safety_buffer_pct))
    return max(min_safety_buffer, pct_buffer)


def _compute_severity(
    shortage_point: int,
    demand_point: Decimal,
) -> ShortageSeverity:
    """Map shortage magnitude to a severity tier."""
    if shortage_point == 0:
        return ShortageSeverity.NONE
    if demand_point <= 0:
        return ShortageSeverity.CRITICAL
    ratio = Decimal(shortage_point) / demand_point
    if ratio < _SEVERITY_LOW:
        return ShortageSeverity.LOW
    if ratio < _SEVERITY_MEDIUM:
        return ShortageSeverity.MEDIUM
    if ratio < _SEVERITY_HIGH:
        return ShortageSeverity.HIGH
    return ShortageSeverity.CRITICAL


def _stockout_window_fraction(
    available_for_demand: int,
    demand_point: Decimal,
) -> Decimal | None:
    """Estimate fraction of window demand serviceable before stockout.

    Returns ``None`` when no stockout is projected.  When a stockout is
    projected, returns ``available_for_demand / demand_point`` clamped
    to ``[0, 1)``, representing the fraction of the window over which
    supply is sufficient (assuming uniform demand rate).
    """
    if available_for_demand <= 0:
        return _ZERO
    if demand_point <= 0:
        return None
    fraction = Decimal(available_for_demand) / demand_point
    if fraction >= 1:
        return None  # no stockout
    return fraction.quantize(_DP, rounding=ROUND_HALF_UP)


def _stockout_fraction_from_curve(
    available_for_demand: int,
    demand_point: Decimal,
    cumulative_demand_curve: tuple[Decimal, ...],
) -> Decimal | None:
    """Interpolate stockout fraction from cumulative demand checkpoints."""
    if not cumulative_demand_curve:
        raise ValueError("cumulative_demand_curve cannot be empty")
    previous = Decimal("0")
    for value in cumulative_demand_curve:
        if not value.is_finite() or value < previous:
            raise ValueError("cumulative demand curve must be finite and non-decreasing")
        previous = value
    if abs(cumulative_demand_curve[-1] - demand_point) > _DP:
        raise ValueError("cumulative demand curve must end at point_demand")
    if available_for_demand <= 0:
        return _ZERO
    if Decimal(available_for_demand) >= demand_point:
        return None

    checkpoints = Decimal(len(cumulative_demand_curve))
    prior_quantity = Decimal("0")
    prior_fraction = Decimal("0")
    for index, quantity in enumerate(cumulative_demand_curve, start=1):
        current_fraction = Decimal(index) / checkpoints
        if quantity >= Decimal(available_for_demand):
            increment = quantity - prior_quantity
            if increment == 0:
                return prior_fraction.quantize(_DP, rounding=ROUND_HALF_UP)
            within = (Decimal(available_for_demand) - prior_quantity) / increment
            result = prior_fraction + within * (current_fraction - prior_fraction)
            return result.quantize(_DP, rounding=ROUND_HALF_UP)
        prior_quantity = quantity
        prior_fraction = current_fraction
    return None


def _compute_projection_id(
    forecast_id: str,
    opening_inventory: int,
    replenishment_quantity: int,
    safety_buffer: int,
    rule_version: str,
    stockout_timing_method: StockoutTimingMethod,
    cumulative_demand_curve: tuple[Decimal, ...] | None,
) -> str:
    """Deterministic SHA-256 projection identifier."""
    payload = {
        "fi": forecast_id,
        "oi": opening_inventory,
        "rq": replenishment_quantity,
        "rv": rule_version,
        "sb": safety_buffer,
        "stm": stockout_timing_method.value,
        "curve": (
            None
            if cumulative_demand_curve is None
            else [str(value) for value in cumulative_demand_curve]
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tag = sha256(encoded).hexdigest()[:16]
    return f"inv_{tag}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def project_inventory(
    forecast: ForecastLike,
    *,
    opening_inventory: int,
    replenishment_quantity: int = 0,
    safety_buffer_pct: Decimal = DEFAULT_SAFETY_BUFFER_PCT,
    min_safety_buffer: int = DEFAULT_MIN_SAFETY_BUFFER,
    surplus_risk_multiplier: Decimal = DEFAULT_SURPLUS_RISK_MULTIPLIER,
    unit: str = "portions",
    rule_version: str = RULE_VERSION,
    evidence_ids: tuple[str, ...] = (),
    cumulative_demand_curve: tuple[Decimal, ...] | None = None,
) -> InventoryProjection:
    """Project inventory outcomes from a demand forecast.

    Parameters
    ----------
    forecast:
        A ``ForecastResult`` with point, lower and upper demand estimates.
    opening_inventory:
        Current usable inventory count before the service window.
    replenishment_quantity:
        Inventory expected to arrive before the window.
    safety_buffer_pct:
        Fraction of opening inventory to reserve as safety stock.
    min_safety_buffer:
        Absolute minimum safety buffer regardless of pct calculation.
    surplus_risk_multiplier:
        Flag surplus risk when surplus_point exceeds
        ``safety_buffer × surplus_risk_multiplier``.
    unit:
        Inventory unit label.
    rule_version:
        Algorithm version carried on the projection for traceability.
    evidence_ids:
        IDs of input signals or records that inform this projection.
    """
    if opening_inventory < 0:
        raise ValueError("opening_inventory must be non-negative")
    if replenishment_quantity < 0:
        raise ValueError("replenishment_quantity must be non-negative")

    # --- Supply arithmetic -------------------------------------------------
    usable_supply = opening_inventory + replenishment_quantity
    safety_buffer = _compute_safety_buffer(
        opening_inventory, safety_buffer_pct, min_safety_buffer
    )
    available_for_demand = max(0, usable_supply - safety_buffer)

    # --- Demand scenarios (rounded to nearest integer) ---------------------
    demand_point_int = max(0, int(forecast.point_demand.to_integral_value(rounding=ROUND_HALF_UP)))
    demand_lower_int = max(0, int(forecast.lower_demand.to_integral_value(rounding=ROUND_HALF_UP)))
    demand_upper_int = max(0, int(forecast.upper_demand.to_integral_value(rounding=ROUND_HALF_UP)))

    # Ending inventory = usable_supply - demand (may be negative → shortage)
    ending_inventory_point = usable_supply - demand_point_int
    ending_inventory_lower = usable_supply - demand_upper_int  # worst-case (high demand)
    ending_inventory_upper = usable_supply - demand_lower_int  # best-case (low demand)

    # --- Shortage (unmet demand after respecting safety buffer) ------------
    shortage_point = max(0, demand_point_int - available_for_demand)
    shortage_upper = max(0, demand_upper_int - available_for_demand)  # worst-case

    # --- Surplus (demand below available, leaving excess stock) ------------
    surplus_point = max(0, available_for_demand - demand_point_int)
    surplus_lower = max(0, available_for_demand - demand_upper_int)  # worst-case

    # --- Risk assessment ---------------------------------------------------
    stockout_risk = shortage_point > 0
    shortage_severity = _compute_severity(shortage_point, forecast.point_demand)
    surplus_threshold = int(safety_buffer * float(surplus_risk_multiplier))
    surplus_risk = surplus_point > surplus_threshold

    # --- Stockout-window fraction (only when stockout is projected) --------
    fraction: Decimal | None
    timing_method = (
        StockoutTimingMethod.CUMULATIVE_CURVE
        if cumulative_demand_curve is not None
        else StockoutTimingMethod.UNIFORM_FALLBACK
    )
    if stockout_risk and cumulative_demand_curve is not None:
        fraction = _stockout_fraction_from_curve(
            available_for_demand, forecast.point_demand, cumulative_demand_curve
        )
    elif stockout_risk:
        fraction = _stockout_window_fraction(available_for_demand, forecast.point_demand)
    else:
        if cumulative_demand_curve is not None:
            _stockout_fraction_from_curve(
                available_for_demand, forecast.point_demand, cumulative_demand_curve
            )
        fraction = None

    # --- Deterministic identity -------------------------------------------
    projection_id = _compute_projection_id(
        forecast.forecast_id,
        opening_inventory,
        replenishment_quantity,
        safety_buffer,
        rule_version,
        timing_method,
        cumulative_demand_curve,
    )

    return InventoryProjection(
        projection_id=projection_id,
        forecast_id=forecast.forecast_id,
        outlet_id=forecast.outlet_id,
        sku_id=forecast.sku_id,
        service_window=forecast.service_window,
        window_start=forecast.window_start,
        window_end=forecast.window_end,
        opening_inventory=opening_inventory,
        replenishment_quantity=replenishment_quantity,
        usable_supply=usable_supply,
        safety_buffer=safety_buffer,
        available_for_demand=available_for_demand,
        ending_inventory_point=ending_inventory_point,
        ending_inventory_lower=ending_inventory_lower,
        ending_inventory_upper=ending_inventory_upper,
        shortage_point=shortage_point,
        shortage_upper=shortage_upper,
        surplus_point=surplus_point,
        surplus_lower=surplus_lower,
        stockout_risk=stockout_risk,
        shortage_severity=shortage_severity,
        surplus_risk=surplus_risk,
        stockout_window_fraction=fraction,
        stockout_timing_method=timing_method,
        unit=unit,
        rule_version=rule_version,
        evidence_ids=evidence_ids,
    )
