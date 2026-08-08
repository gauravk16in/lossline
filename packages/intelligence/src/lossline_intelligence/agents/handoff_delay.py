"""Deterministic handoff-delay-spike detector.

Responsibility
--------------
Given the mean handoff wait time (seconds) in the current window versus the
historical baseline, decide whether delivery handoff is degraded.

Trigger conditions (both must be met):
  1. handoff_count >= 8              (minimum sample guard)
  2. current_mean >= baseline × 1.40 (ratio threshold)

Severity brackets (ratio above baseline):
  1.40x – 1.59x  → LOW
  1.60x – 1.99x  → MEDIUM
  2.00x – 2.49x  → HIGH
  2.50x +        → CRITICAL
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from lossline_intelligence.models.signal import (
    SEVERITY_SCORE,
    Severity,
    Signal,
    SignalType,
)

MIN_HANDOFF_COUNT = 8
RATIO_THRESHOLD = 1.40
DETECTOR_VERSION = "handoff_delay_spike.v1"

_SEVERITY_BRACKETS: list[tuple[float, Severity]] = [
    (2.50, Severity.CRITICAL),
    (2.00, Severity.HIGH),
    (1.60, Severity.MEDIUM),
    (1.40, Severity.LOW),
]


@dataclass(frozen=True)
class HandoffDelayMetrics:
    """Input value object for the handoff-delay detector.

    Attributes
    ----------
    restaurant_id        : Restaurant identifier.
    current_mean_seconds : Mean handoff wait in the observation window.
    baseline_mean_seconds: Historical mean handoff wait (same time band).
    handoff_count        : Handoffs completed in the window.
    window_start         : UTC-aware window start.
    window_end           : UTC-aware window end.
    evidence_ids         : Non-empty unique event IDs for handoffs.
    """

    outlet_id: str
    current_mean_seconds: float
    baseline_mean_seconds: float
    handoff_count: int
    window_start: datetime
    window_end: datetime
    evidence_ids: tuple[str, ...]


def _classify_ratio(ratio: float) -> Severity | None:
    for threshold, severity in _SEVERITY_BRACKETS:
        if ratio >= threshold:
            return severity
    return None


def detect_handoff_delay_spike(metrics: HandoffDelayMetrics) -> Signal | None:
    """Detect whether mean handoff wait time is abnormally high.

    Returns Signal if all conditions fire, None otherwise.

    Raises
    ------
    ValueError  If baseline_mean_seconds is not positive.
    """
    if metrics.baseline_mean_seconds <= 0:
        raise ValueError(
            f"baseline_mean_seconds must be > 0, got {metrics.baseline_mean_seconds!r}"
        )
    if metrics.handoff_count < MIN_HANDOFF_COUNT:
        return None

    ratio = metrics.current_mean_seconds / metrics.baseline_mean_seconds
    severity = _classify_ratio(ratio)
    if severity is None:
        return None

    confidence: float = SEVERITY_SCORE[severity]

    current_dec = Decimal(str(metrics.current_mean_seconds))
    baseline_dec = Decimal(str(metrics.baseline_mean_seconds))
    window_tag = metrics.window_start.strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"sig_handoff_delay_{metrics.outlet_id}_{window_tag}"

    return Signal.model_validate(
        {
            "signal_id": signal_id,
            "outlet_id": metrics.outlet_id,
            "signal_type": SignalType.HANDOFF_DELAY_SPIKE,
            "severity": confidence,
            "current_value": current_dec,
            "baseline_value": baseline_dec,
            "deviation_ratio": (current_dec - baseline_dec) / baseline_dec,
            "unit": "seconds",
            "window_start": metrics.window_start,
            "window_end": metrics.window_end,
            "evidence_event_ids": metrics.evidence_ids,
            "detector_version": DETECTOR_VERSION,
        }
    )
