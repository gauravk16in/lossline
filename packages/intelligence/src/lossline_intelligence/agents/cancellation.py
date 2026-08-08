"""Deterministic cancellation-spike detector.

Responsibility
--------------
Given the current cancellation rate and a baseline rate for one outlet
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
from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite
from typing import NamedTuple

from lossline_intelligence.models.signal import Signal, SignalType, Severity, SEVERITY_SCORE


_THRESHOLDS: tuple[tuple[Decimal, Severity], ...] = (
    (Decimal("1.50"), Severity.CRITICAL),
    (Decimal("1.00"), Severity.HIGH),
    (Decimal("0.50"), Severity.MEDIUM),
    (Decimal("0.25"), Severity.LOW),
)

DETECTOR_VERSION = "cancellation_spike.v1"


@dataclass(frozen=True)
class CancellationMetrics:
    """Input value object for the cancellation detector.

    Attributes
    ----------
    outlet_id       : Identifier for the outlet.
    current_rate    : Observed cancellation rate in the current window
                      (e.g. 0.18 means 18 %).
    baseline_rate   : Expected cancellation rate from historical data
                      (e.g. 0.07 means 7 %).
    window_start    : UTC-aware start of the observation window.
    window_end      : UTC-aware end of the observation window.
    evidence_ids    : One or more event IDs that contributed to this metric.
                      Must be non-empty and contain no duplicates.
    """

    outlet_id: str
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


def _classify_deviation(deviation_ratio: Decimal) -> Severity | None:
    """Map a deviation ratio to a severity label, or None if normal."""
    for threshold, severity in _THRESHOLDS:
        if deviation_ratio >= threshold:
            return severity
    return None


def _validate_metrics(metrics: CancellationMetrics) -> None:
    """Validate detector inputs before deciding whether to emit a signal."""
    if not metrics.outlet_id.strip():
        raise ValueError("outlet_id must be non-empty")
    if not isfinite(metrics.current_rate) or not 0 <= metrics.current_rate <= 1:
        raise ValueError("current_rate must be finite and between 0 and 1")
    if not isfinite(metrics.baseline_rate) or not 0 < metrics.baseline_rate <= 1:
        raise ValueError("baseline_rate must be finite, greater than 0, and at most 1")
    if metrics.window_start.tzinfo is None or metrics.window_start.utcoffset() is None:
        raise ValueError("window_start must include a UTC offset")
    if metrics.window_end.tzinfo is None or metrics.window_end.utcoffset() is None:
        raise ValueError("window_end must include a UTC offset")
    if metrics.window_end <= metrics.window_start:
        raise ValueError("window_end must be after window_start")
    if not metrics.evidence_ids:
        raise ValueError("evidence_ids must not be empty")
    if len(metrics.evidence_ids) != len(set(metrics.evidence_ids)):
        raise ValueError("evidence_ids must be unique")
    if any(not event_id.strip() for event_id in metrics.evidence_ids):
        raise ValueError("evidence_ids must contain non-empty identifiers")


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
    _validate_metrics(metrics)

    current_dec = Decimal(str(metrics.current_rate))
    baseline_dec = Decimal(str(metrics.baseline_rate))
    deviation_ratio = (current_dec - baseline_dec) / baseline_dec

    severity = _classify_deviation(deviation_ratio)
    if severity is None:
        return None

    # Confidence is a deterministic heuristic — never exceeds 0.95.
    # This is NOT a statistically validated probability.
    confidence: float = SEVERITY_SCORE[severity]

    deviation_pct = deviation_ratio * Decimal("100")

    message = (
        f"CANCELLATION_SPIKE detected: {metrics.current_rate:.1%} current vs "
        f"{metrics.baseline_rate:.1%} baseline "
        f"({deviation_pct:.2f}% deviation, severity={severity.value})."
    )

    # Build a deterministic signal_id so replaying identical metrics yields
    # the same ID (idempotency-friendly).
    window_tag = metrics.window_start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"sig_cancellation_{metrics.outlet_id}_{window_tag}"

    signal = Signal.model_validate(
        {
            "signal_id": signal_id,
            "outlet_id": metrics.outlet_id,
            "signal_type": SignalType.CANCELLATION_SPIKE,
            "severity": confidence,
            "current_value": current_dec,
            "baseline_value": baseline_dec,
            "deviation_ratio": deviation_ratio,
            "unit": "ratio",
            "window_start": metrics.window_start,
            "window_end": metrics.window_end,
            "evidence_event_ids": metrics.evidence_ids,
            "detector_version": DETECTOR_VERSION,
            "metadata": {
                "threshold_ratio": str(_THRESHOLDS[-1][0]),
                "severity_band": severity.value,
            },
        }
    )

    return CancellationSignal(
        signal=signal,
        severity=severity,
        deviation_percent=round(float(deviation_pct), 4),
        message=message,
    )
