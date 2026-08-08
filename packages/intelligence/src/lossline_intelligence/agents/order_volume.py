"""Deterministic order-volume-spike detector.

Responsibility
--------------
Given the current order rate, baseline, historical samples, and order count
for one restaurant window, decide whether the volume spike is significant.

Trigger conditions (all must be met):
  1. order_count >= 10               (minimum sample guard)
  2. current_rate >= baseline × 1.30 (ratio threshold)
  3. robust z-score >= 2.0           (statistical significance via MAD)

Severity brackets (ratio above baseline):
  1.30x – 1.49x  → LOW
  1.50x – 1.99x  → MEDIUM
  2.00x – 2.49x  → HIGH
  2.50x +        → CRITICAL
"""

import statistics
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from lossline_intelligence.models.signal import (
    SEVERITY_SCORE,
    Severity,
    Signal,
    SignalType,
)

MIN_ORDER_COUNT = 10
RATIO_THRESHOLD = 1.30
Z_SCORE_THRESHOLD = 2.0
DETECTOR_VERSION = "order_volume_spike.v1"

_SEVERITY_BRACKETS: list[tuple[float, Severity]] = [
    (2.50, Severity.CRITICAL),
    (2.00, Severity.HIGH),
    (1.50, Severity.MEDIUM),
    (1.30, Severity.LOW),
]


@dataclass(frozen=True)
class OrderVolumeMetrics:
    """Input value object for the order-volume detector.

    Attributes
    ----------
    restaurant_id      : Restaurant identifier.
    current_rate       : Orders per minute in the observation window.
    baseline_rate      : Median historical orders per minute (same time band).
    baseline_samples   : Raw historical per-window rates used for MAD/z-score.
                         Must have at least 2 elements for z-score to be meaningful.
    order_count        : Total orders placed in the observation window.
    window_start       : UTC-aware window start.
    window_end         : UTC-aware window end.
    evidence_ids       : Non-empty unique event IDs contributing to this metric.
    """

    outlet_id: str
    current_rate: float
    baseline_rate: float
    baseline_samples: tuple[float, ...]
    order_count: int
    window_start: datetime
    window_end: datetime
    evidence_ids: tuple[str, ...]


def _robust_z_score(current: float, samples: list[float]) -> float:
    """Compute a MAD-based robust z-score.

    Returns 0.0 when there are fewer than 2 samples or MAD is zero
    (no variance means we cannot distinguish signal from noise here).
    """
    if len(samples) < 2:
        return 0.0
    med = statistics.median(samples)
    mad = statistics.median([abs(x - med) for x in samples])
    if mad == 0.0:
        return 0.0
    return (current - med) / (1.4826 * mad)


def _classify_ratio(ratio: float) -> Severity | None:
    for threshold, severity in _SEVERITY_BRACKETS:
        if ratio >= threshold:
            return severity
    return None


def detect_order_volume_spike(metrics: OrderVolumeMetrics) -> Signal | None:
    """Detect whether the order rate is abnormally elevated.

    Returns Signal if all three conditions fire, None otherwise.

    Raises
    ------
    ValueError  If baseline_rate is not positive.
    """
    if metrics.baseline_rate <= 0:
        raise ValueError(
            f"baseline_rate must be > 0, got {metrics.baseline_rate!r}"
        )

    # Guard: not enough orders to be statistically meaningful
    if metrics.order_count < MIN_ORDER_COUNT:
        return None

    ratio = metrics.current_rate / metrics.baseline_rate
    severity = _classify_ratio(ratio)
    if severity is None:
        return None  # below ratio threshold

    z = _robust_z_score(metrics.current_rate, list(metrics.baseline_samples))
    if z < Z_SCORE_THRESHOLD:
        return None  # ratio met but not statistically significant

    confidence: float = SEVERITY_SCORE[severity]

    current_dec = Decimal(str(metrics.current_rate))
    baseline_dec = Decimal(str(metrics.baseline_rate))
    window_tag = metrics.window_start.strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"sig_order_volume_{metrics.outlet_id}_{window_tag}"

    return Signal.model_validate(
        {
            "signal_id": signal_id,
            "outlet_id": metrics.outlet_id,
            "signal_type": SignalType.ORDER_VOLUME_SPIKE,
            "severity": confidence,
            "current_value": current_dec,
            "baseline_value": baseline_dec,
            "deviation_ratio": (current_dec - baseline_dec) / baseline_dec,
            "unit": "orders_per_minute",
            "window_start": metrics.window_start,
            "window_end": metrics.window_end,
            "evidence_event_ids": metrics.evidence_ids,
            "detector_version": DETECTOR_VERSION,
        }
    )
