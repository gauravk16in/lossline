"""Deterministic capacity projection engine.

``project_capacity`` takes a demand forecast, per-SKU workload parameters,
and available station capacity, then projects utilization scenarios and
assesses the capacity risk tier.

Architecture: outlet capacity is a shared resource across all SKUs.
The engine receives aggregated workload_minutes_per_unit for each forecasted
SKU and combines them against the window's available station-minutes.
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json

from lossline_intelligence.capacity.projection import (
    CapacityProjection,
    CapacityRiskTier,
)

# ---------------------------------------------------------------------------
# Rule version
# ---------------------------------------------------------------------------

RULE_VERSION = "capacity.v1"

# ---------------------------------------------------------------------------
# Default thresholds (module-level constants, overridable by caller)
# ---------------------------------------------------------------------------

DEFAULT_BASE_PREP_MINUTES: Decimal = Decimal("15")
DEFAULT_EFFICIENCY_FACTOR: Decimal = Decimal("0.85")

# Risk tier thresholds (utilization ratio)
_TIER_MODERATE: Decimal = Decimal("0.70")
_TIER_HIGH: Decimal = Decimal("0.90")
_TIER_CRITICAL: Decimal = Decimal("1.00")

_DP = Decimal("0.0001")
_ZERO = Decimal("0")
_ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_risk_tier(utilization: Decimal) -> CapacityRiskTier:
    """Map utilization ratio to a capacity risk tier."""
    if utilization >= _TIER_CRITICAL:
        return CapacityRiskTier.CRITICAL
    if utilization >= _TIER_HIGH:
        return CapacityRiskTier.HIGH
    if utilization >= _TIER_MODERATE:
        return CapacityRiskTier.MODERATE
    return CapacityRiskTier.SAFE


def _safe_utilization(workload: Decimal, effective_capacity: Decimal) -> Decimal:
    """Compute utilization, returning 0 when effective_capacity is zero."""
    if effective_capacity <= _ZERO:
        return _ZERO
    return (workload / effective_capacity).quantize(_DP, rounding=ROUND_HALF_UP)


def _compute_projection_id(
    forecast_id: str,
    available_capacity_minutes: Decimal,
    efficiency_factor: Decimal,
    rule_version: str,
) -> str:
    """Deterministic SHA-256 capacity projection identifier."""
    payload = {
        "ac": str(available_capacity_minutes),
        "ef": str(efficiency_factor),
        "fi": forecast_id,
        "rv": rule_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tag = sha256(encoded).hexdigest()[:16]
    return f"cap_{tag}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@staticmethod
def _workload(demand_qty: Decimal, workload_minutes_per_unit: Decimal) -> Decimal:
    """Total workload for one SKU at a given demand scenario."""
    return (demand_qty * workload_minutes_per_unit).quantize(_DP, rounding=ROUND_HALF_UP)


def project_capacity(
    *,
    forecast_id: str,
    outlet_id: str,
    service_window: str,
    window_start,
    window_end,
    # SKU workload specification: list of (demand_point, demand_lower,
    # demand_upper, workload_minutes_per_unit) tuples
    sku_workloads: tuple[tuple[Decimal, Decimal, Decimal, Decimal], ...],
    available_capacity_minutes: Decimal,
    base_prep_minutes: Decimal = DEFAULT_BASE_PREP_MINUTES,
    efficiency_factor: Decimal = DEFAULT_EFFICIENCY_FACTOR,
    rule_version: str = RULE_VERSION,
    evidence_ids: tuple[str, ...] = (),
) -> CapacityProjection:
    """Project capacity utilization for one outlet × window.

    Parameters
    ----------
    forecast_id:
        Forecast that triggered this projection (for traceability).
    outlet_id:
        Outlet identifier.
    service_window:
        Named service window.
    window_start / window_end:
        Timezone-aware UTC window boundaries.
    sku_workloads:
        Sequence of ``(demand_point, demand_lower, demand_upper,
        workload_minutes_per_unit)`` tuples — one entry per SKU.
        All demand values come from the corresponding forecast.
    available_capacity_minutes:
        Total station-minutes available for the window.
    base_prep_minutes:
        Baseline mean preparation time without congestion.
    efficiency_factor:
        Fraction of capacity usable after setup/changeover overhead.
    rule_version:
        Algorithm version carried on the projection for traceability.
    evidence_ids:
        IDs of input signals or records that inform this projection.
    """
    if available_capacity_minutes <= _ZERO:
        raise ValueError("available_capacity_minutes must be positive")
    if not available_capacity_minutes.is_finite():
        raise ValueError("available_capacity_minutes must be finite")
    if not (Decimal("0") < efficiency_factor <= Decimal("1")):
        raise ValueError("efficiency_factor must be in (0, 1]")
    if not sku_workloads:
        raise ValueError("at least one SKU workload is required")

    # --- Aggregate workload across all SKUs for each scenario ----------------
    total_point = _ZERO
    total_lower = _ZERO
    total_upper = _ZERO
    for demand_point, demand_lower, demand_upper, per_unit in sku_workloads:
        total_point = total_point + _workload(demand_point, per_unit)
        total_lower = total_lower + _workload(demand_lower, per_unit)
        total_upper = total_upper + _workload(demand_upper, per_unit)

    # --- Effective capacity after efficiency overhead -----------------------
    effective_capacity = (available_capacity_minutes * efficiency_factor).quantize(
        _DP, rounding=ROUND_HALF_UP
    )

    # --- Utilization ratios ------------------------------------------------
    util_point = _safe_utilization(total_point, effective_capacity)
    util_lower = _safe_utilization(total_lower, effective_capacity)
    util_upper = _safe_utilization(total_upper, effective_capacity)

    # --- Congestion and mean preparation time ------------------------------
    congestion = max(_ONE, util_point)
    mean_prep = (base_prep_minutes * congestion).quantize(_DP, rounding=ROUND_HALF_UP)

    # --- Risk assessment (based on point-forecast utilization) -------------
    risk_tier = _compute_risk_tier(util_point)
    overloaded = util_point >= _ONE

    # --- Deterministic identity -------------------------------------------
    projection_id = _compute_projection_id(
        forecast_id, available_capacity_minutes, efficiency_factor, rule_version
    )

    return CapacityProjection(
        projection_id=projection_id,
        forecast_id=forecast_id,
        outlet_id=outlet_id,
        service_window=service_window,
        window_start=window_start,
        window_end=window_end,
        demand_workload_point=total_point,
        demand_workload_lower=total_lower,
        demand_workload_upper=total_upper,
        available_capacity_minutes=available_capacity_minutes,
        effective_capacity_minutes=effective_capacity,
        utilization_point=util_point,
        utilization_lower=util_lower,
        utilization_upper=util_upper,
        congestion_factor=congestion,
        mean_preparation_minutes=mean_prep,
        risk_tier=risk_tier,
        overloaded=overloaded,
        rule_version=rule_version,
        evidence_ids=evidence_ids,
    )
