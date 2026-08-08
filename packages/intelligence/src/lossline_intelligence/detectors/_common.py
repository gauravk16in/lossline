"""Shared utilities for deterministic M1 detectors.

These helpers remove boilerplate (outlet guard, signal IDs, z-score math)
without encoding any detector-specific trigger semantics.
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP

from lossline_intelligence.aggregation.baseline import BaselineResult
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot

#: Decimal rounding precision shared by all detectors.
_DP = Decimal("0.0001")

#: Scale factor converting MAD to a robust standard-deviation estimate.
_MAD_SCALE = Decimal("1.4826")


def require_matching_outlet(snapshot: MetricSnapshot, baseline: BaselineResult) -> None:
    """Raise ValueError when snapshot and baseline belong to different outlets."""
    if snapshot.outlet_id != baseline.outlet_id:
        raise ValueError(
            f"outlet mismatch: snapshot.outlet_id={snapshot.outlet_id!r} "
            f"!= baseline.outlet_id={baseline.outlet_id!r}"
        )


def window_tag(snapshot: MetricSnapshot) -> str:
    """UTC window-start tag used in deterministic signal IDs."""
    return snapshot.window_start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_signal_id(prefix: str, snapshot: MetricSnapshot, detector_version: str) -> str:
    """Build a deterministic, idempotency-friendly signal ID."""
    return f"sig_{prefix}_{snapshot.outlet_id}_{window_tag(snapshot)}_{detector_version}"


def quantize(value: Decimal) -> Decimal:
    return value.quantize(_DP, rounding=ROUND_HALF_UP)


def window_minutes(snapshot: MetricSnapshot) -> Decimal:
    """Return the analysis window length in minutes."""
    seconds = (snapshot.window_end - snapshot.window_start).total_seconds()
    if seconds <= 0:
        raise ValueError("window duration must be positive")
    return Decimal(str(seconds / 60.0))


def orders_per_minute(order_count: int, snapshot: MetricSnapshot) -> Decimal:
    """Convert a window order count to an orders-per-minute rate."""
    return quantize(Decimal(str(order_count)) / window_minutes(snapshot))


def robust_z_score(
    current: Decimal,
    median: Decimal | None,
    mad: Decimal | None,
) -> Decimal:
    """MAD-based robust z-score; returns 0 when MAD is unavailable or zero."""
    if median is None or mad is None or mad == Decimal("0"):
        return Decimal("0")
    return quantize((current - median) / (_MAD_SCALE * mad))


def ratio_severity(ratio: Decimal, severity_scale: Decimal) -> float:
    """Map an excess ratio to severity in [0, 1], capped at 1.0."""
    capped = min(Decimal("1.0"), quantize(ratio / severity_scale))
    return float(capped)


def deviation_ratio(current: Decimal, baseline: Decimal) -> Decimal:
    """Relative change; returns 0 when baseline is zero to avoid division by zero."""
    if baseline == Decimal("0"):
        return Decimal("0")
    return quantize((current - baseline) / baseline)
