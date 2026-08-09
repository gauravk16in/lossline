"""Deterministic capacity projection engine.

``project_capacity`` takes a demand forecast, per-SKU workload parameters,
and available station capacity, then projects utilization scenarios and
assesses the capacity risk tier.

Architecture: outlet capacity is a shared resource across all SKUs.
The engine receives aggregated workload_minutes_per_unit for each forecasted
SKU and combines them against the window's available station-minutes.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
DEFAULT_TIER_MODERATE: Decimal = Decimal("0.70")
DEFAULT_TIER_HIGH: Decimal = Decimal("0.90")
DEFAULT_TIER_CRITICAL: Decimal = Decimal("1.00")

_DP = Decimal("0.0001")
_ZERO = Decimal("0")
_ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_risk_tier(
    utilization: Decimal,
    *,
    moderate_threshold: Decimal = DEFAULT_TIER_MODERATE,
    high_threshold: Decimal = DEFAULT_TIER_HIGH,
    critical_threshold: Decimal = DEFAULT_TIER_CRITICAL,
) -> CapacityRiskTier:
    """Map utilization ratio to a capacity risk tier."""
    if utilization >= critical_threshold:
        return CapacityRiskTier.CRITICAL
    if utilization >= high_threshold:
        return CapacityRiskTier.HIGH
    if utilization >= moderate_threshold:
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


def _workload(demand_qty: Decimal, workload_minutes_per_unit: Decimal) -> Decimal:
    """Total workload for one SKU at a given demand scenario."""
    return (demand_qty * workload_minutes_per_unit).quantize(_DP, rounding=ROUND_HALF_UP)


def project_capacity(
    *,
    forecast_id: str,
    outlet_id: str,
    service_window: str,
    window_start: datetime,
    window_end: datetime,
    # SKU workload specification: list of (demand_point, demand_lower,
    # demand_upper, workload_minutes_per_unit) tuples
    sku_workloads: tuple[tuple[Decimal, Decimal, Decimal, Decimal], ...],
    available_capacity_minutes: Decimal,
    base_prep_minutes: Decimal = DEFAULT_BASE_PREP_MINUTES,
    efficiency_factor: Decimal = DEFAULT_EFFICIENCY_FACTOR,
    moderate_threshold: Decimal = DEFAULT_TIER_MODERATE,
    high_threshold: Decimal = DEFAULT_TIER_HIGH,
    critical_threshold: Decimal = DEFAULT_TIER_CRITICAL,
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
    for name, value in (
        ("available_capacity_minutes", available_capacity_minutes),
        ("base_prep_minutes", base_prep_minutes),
        ("efficiency_factor", efficiency_factor),
        ("moderate_threshold", moderate_threshold),
        ("high_threshold", high_threshold),
        ("critical_threshold", critical_threshold),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError(f"{name} must be a finite Decimal")
    if available_capacity_minutes <= _ZERO:
        raise ValueError("available_capacity_minutes must be positive")
    if base_prep_minutes <= _ZERO:
        raise ValueError("base_prep_minutes must be positive")
    if not (Decimal("0") < efficiency_factor <= Decimal("1")):
        raise ValueError("efficiency_factor must be in (0, 1]")
    if not (_ZERO < moderate_threshold < high_threshold < critical_threshold):
        raise ValueError("risk thresholds must satisfy 0 < moderate < high < critical")
    if not sku_workloads:
        raise ValueError("at least one SKU workload is required")
    for name, value in (
        ("forecast_id", forecast_id),
        ("outlet_id", outlet_id),
        ("service_window", service_window),
        ("rule_version", rule_version),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be non-empty")
    if window_start.tzinfo is None or window_start.utcoffset() is None:
        raise ValueError("window_start must be timezone-aware")
    if window_end.tzinfo is None or window_end.utcoffset() is None:
        raise ValueError("window_end must be timezone-aware")
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    if len(set(evidence_ids)) != len(evidence_ids) or any(
        not isinstance(item, str) or not item.strip() for item in evidence_ids
    ):
        raise ValueError("evidence_ids must be non-empty and unique")

    # --- Aggregate workload across all SKUs for each scenario ----------------
    total_point = _ZERO
    total_lower = _ZERO
    total_upper = _ZERO
    for demand_point, demand_lower, demand_upper, per_unit in sku_workloads:
        values = (demand_point, demand_lower, demand_upper, per_unit)
        if any(not isinstance(value, Decimal) or not value.is_finite() for value in values):
            raise ValueError("SKU workload values must be finite Decimals")
        if demand_lower < _ZERO or demand_point < demand_lower or demand_upper < demand_point:
            raise ValueError("SKU demand must satisfy 0 <= lower <= point <= upper")
        if per_unit <= _ZERO:
            raise ValueError("workload_minutes_per_unit must be positive")
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
    risk_tier = _compute_risk_tier(
        util_point,
        moderate_threshold=moderate_threshold,
        high_threshold=high_threshold,
        critical_threshold=critical_threshold,
    )
    overloaded = util_point >= _ONE

    # --- Deterministic identity -------------------------------------------
    identity_payload = {
        "forecast_id": forecast_id,
        "outlet_id": outlet_id,
        "service_window": service_window,
        "window_start": window_start.astimezone(timezone.utc).isoformat(),
        "window_end": window_end.astimezone(timezone.utc).isoformat(),
        "sku_workloads": [[str(value) for value in row] for row in sku_workloads],
        "available_capacity_minutes": str(available_capacity_minutes),
        "base_prep_minutes": str(base_prep_minutes),
        "efficiency_factor": str(efficiency_factor),
        "risk_thresholds": [str(moderate_threshold), str(high_threshold), str(critical_threshold)],
        "rule_version": rule_version,
        "evidence_ids": list(evidence_ids),
    }
    encoded = json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    projection_id = f"cap_{sha256(encoded).hexdigest()[:16]}"

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
