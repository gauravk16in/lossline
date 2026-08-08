"""Deterministic cancellation-spike detector.

Responsibility
--------------
Given the current cancellation rate and a baseline rate for one restaurant
window, decide whether the deviation is large enough to raise a Signal.

What this module does NOT do
----------------------------
- It does not infer *why* cancellations spiked (no root-cause reasoning).
- It does not connect to any database, Redis, or external service.
- It does not call any LLM.

Threshold table
---------------
deviation < 25 %          → None  (normal variance, no signal)
25 % – 49.99 %            → LOW
50 % – 99.99 %            → MEDIUM
100 % – 149.99 %          → HIGH
150 % +                   → CRITICAL
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from lossline_intelligence.models.signal import (
    SEVERITY_SCORE,
    Severity,
    Signal,
    SignalType,
)

# Threshold table: (minimum_deviation_pct, severity_label)
# Listed highest-first so the first match wins.
_THRESHOLDS: list[tuple[float, Severity]] = [
    (150.0, Severity.CRITICAL),
    (100.0, Severity.HIGH),
    (50.0, Severity.MEDIUM),
    (25.0, Severity.LOW),
]

DETECTOR_VERSION = "cancellation_spike.v1"


@dataclass(frozen=True)
class CancellationMetrics:
    """Input value object for the cancellation detector.

    Attributes
    ----------
    restaurant_id   : Identifier for the restaurant / outlet.
    current_rate    : Observed cancellation rate in the current window
                      (e.g. 0.18 means 18 %).
    baseline_rate   : Expected cancellation rate from historical data
                      (e.g. 0.07 means 7 %).
    window_start    : UTC-aware start of the observation window.
    window_end      : UTC-aware end of the observation window.
    evidence_ids    : One or more event IDs that contributed to this metric.
                      Must be non-empty and contain no duplicates.
    """

    restaurant_id: str
    current_rate: float
    baseline_rate: float
    window_start: datetime
    window_end: datetime
    evidence_ids: tuple[str, ...]


class CancellationSignal(NamedTuple):
    """Enriched result returned by detect_cancellation_spike.

    Wraps the canonical Signal (which stores severity as a float for ranking)
    with the categorical Severity label and human-readable metadata that
    downstream investigation workflows need directly.
    """

    signal: Signal
    severity: Severity
    deviation_percent: float
    message: str


def _classify_deviation(deviation_pct: float) -> Severity | None:
    """Map a deviation percentage to a Severity label, or None if normal."""
    for threshold, severity in _THRESHOLDS:
        if deviation_pct >= threshold:
            return severity
    return None


def detect_cancellation_spike(
    metrics: CancellationMetrics,
) -> CancellationSignal | None:
    """Detect whether the cancellation rate is abnormally high.

    Parameters
    ----------
    metrics:
        Current and baseline cancellation rates with window metadata.

    Returns
    -------
    CancellationSignal if an anomaly is detected, None if within tolerance.

    Raises
    ------
    ValueError
        If ``baseline_rate`` is not positive (guards against division by zero
        and meaningless deviation values).
    """
    if metrics.baseline_rate <= 0:
        raise ValueError(
            f"baseline_rate must be > 0, got {metrics.baseline_rate!r}. "
            "A zero or negative baseline produces a meaningless deviation."
        )

    deviation_pct: float = (
        (metrics.current_rate - metrics.baseline_rate) / metrics.baseline_rate
    ) * 100.0

    severity = _classify_deviation(deviation_pct)
    if severity is None:
        return None

    # Confidence is a deterministic heuristic — never exceeds 0.95.
    # This is NOT a statistically validated probability.
    confidence: float = SEVERITY_SCORE[severity]

    current_dec = Decimal(str(metrics.current_rate))
    baseline_dec = Decimal(str(metrics.baseline_rate))
    deviation_dec = current_dec - baseline_dec

    message = (
        f"CANCELLATION_SPIKE detected: {metrics.current_rate:.1%} current vs "
        f"{metrics.baseline_rate:.1%} baseline "
        f"({deviation_pct:.2f}% deviation, severity={severity})."
    )

    # Build a deterministic signal_id so replaying identical metrics yields
    # the same ID (idempotency-friendly).
    window_tag = metrics.window_start.strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"sig_cancellation_{metrics.restaurant_id}_{window_tag}"

    signal = Signal.model_validate(
        {
            "signal_id": signal_id,
            "restaurant_id": metrics.restaurant_id,
            "signal_type": SignalType.CANCELLATION_SPIKE,
            "severity": confidence,
            "current_value": current_dec,
            "baseline_value": baseline_dec,
            "deviation": deviation_dec,
            "unit": "ratio",
            "window_start": metrics.window_start,
            "window_end": metrics.window_end,
            "evidence_event_ids": metrics.evidence_ids,
            "detector_version": DETECTOR_VERSION,
        }
    )

    return CancellationSignal(
        signal=signal,
        severity=severity,
        deviation_percent=round(deviation_pct, 4),
        message=message,
    )
