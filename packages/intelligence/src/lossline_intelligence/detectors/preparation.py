"""PREP_TIME_SPIKE deterministic detector.

Responsibility
--------------
Given a current MetricSnapshot and a BaselineResult for the same outlet
and window, decide whether mean preparation time is abnormally high.

Detection Rule (CONFIG_DEFAULT — FINAL_IMPLEMENTATION_PLAN §Detector Specs)
---------------------------------------------------------------------------
Fire only when ALL of the following conditions hold:

  1. Sample sufficiency:
       snapshot.prep_completed_count >= MIN_PREP_COMPLETED_COUNT   (default: 8)

  2. Ratio threshold:
       current avg_prep_minutes >= baseline × RATIO_THRESHOLD   (default: 1.40×)

Zero-baseline handling
-----------------------
When baseline avg_prep_minutes is zero:
  - Ratio is treated as met only when current avg_prep_minutes > 0.
  - deviation_ratio is set to Decimal("0") to avoid division-by-zero.

Severity formula (deterministic, monotonic)
--------------------------------------------
severity = min(1.0, ratio / SEVERITY_SCALE)   where SEVERITY_SCALE = 4.0

Evidence
---------
Uses MetricSnapshot.source_event_ids — all event IDs in the window.
Per-type preparation.completed IDs would require a snapshot schema extension.

Signal ID
----------
Deterministic: ``sig_prep_time_{outlet_id}_{window_start_utc}_{DETECTOR_VERSION}``
"""

from __future__ import annotations

from decimal import Decimal

from lossline_intelligence.aggregation.baseline import BaselineResult
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.detectors._common import (
    build_signal_id,
    deviation_ratio,
    quantize,
    ratio_severity,
    require_matching_outlet,
)
from lossline_intelligence.models.signal import Signal, SignalType

MIN_PREP_COMPLETED_COUNT: int = 8
RATIO_THRESHOLD: Decimal = Decimal("1.40")
SEVERITY_SCALE: Decimal = Decimal("4.0")
DETECTOR_VERSION: str = "prep_time_spike.v1"


def detect_prep_time_spike(
    snapshot: MetricSnapshot,
    baseline: BaselineResult,
    *,
    min_prep_completed_count: int = MIN_PREP_COMPLETED_COUNT,
    ratio_threshold: Decimal = RATIO_THRESHOLD,
    severity_scale: Decimal = SEVERITY_SCALE,
) -> Signal | None:
    """Detect whether mean preparation time is abnormally high."""
    require_matching_outlet(snapshot, baseline)

    if snapshot.prep_completed_count < min_prep_completed_count:
        return None

    if not snapshot.source_event_ids:
        return None

    baseline_mean: Decimal | None = baseline.avg_prep_minutes.median
    if baseline_mean is None:
        return None

    current_mean = snapshot.avg_prep_minutes

    if baseline_mean == Decimal("0"):
        if current_mean <= Decimal("0"):
            return None
        ratio_met = True
        ratio = quantize(current_mean)
        deviation = Decimal("0")
    else:
        ratio = quantize(current_mean / baseline_mean)
        ratio_met = ratio >= ratio_threshold
        deviation = deviation_ratio(current_mean, baseline_mean)

    if not ratio_met:
        return None

    severity = ratio_severity(ratio, severity_scale)

    return Signal.model_validate(
        {
            "signal_id": build_signal_id("prep_time", snapshot, DETECTOR_VERSION),
            "outlet_id": snapshot.outlet_id,
            "signal_type": SignalType.PREP_TIME_SPIKE,
            "severity": severity,
            "current_value": current_mean,
            "baseline_value": baseline_mean,
            "deviation_ratio": deviation,
            "unit": "minutes",
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "evidence_event_ids": snapshot.source_event_ids,
            "detector_version": DETECTOR_VERSION,
            "metadata": {
                "prep_completed_count": snapshot.prep_completed_count,
                "p90_prep_minutes": str(snapshot.p90_prep_minutes),
                "baseline_sample_count": baseline.avg_prep_minutes.sample_count,
                "baseline_sufficient": baseline.sufficient_history,
                "ratio_threshold": str(ratio_threshold),
            },
        }
    )
