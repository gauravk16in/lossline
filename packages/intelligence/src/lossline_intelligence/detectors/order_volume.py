"""ORDER_VOLUME_SPIKE deterministic detector.

Responsibility
--------------
Given a current MetricSnapshot and a BaselineResult for the same outlet
and window, decide whether the order rate is abnormally elevated.

Detection Rule (CONFIG_DEFAULT — FINAL_IMPLEMENTATION_PLAN §Detector Specs)
---------------------------------------------------------------------------
Fire only when ALL of the following conditions hold:

  1. Sample sufficiency:
       snapshot.order_count >= MIN_ORDER_COUNT   (default: 10)

  2. Ratio threshold:
       current_rate >= baseline_rate * RATIO_THRESHOLD   (default: 1.30×)

  3. Robust z-score:
       z-score(current order count) >= Z_SCORE_THRESHOLD   (default: 2.0)

Rates are computed as orders-per-minute over the snapshot window.  Because
numerator and denominator share the same window length, the ratio equals
the raw order-count ratio.

Severity formula (deterministic, monotonic)
--------------------------------------------
severity = min(1.0, ratio / SEVERITY_SCALE)   where SEVERITY_SCALE = 4.0

Evidence
---------
Uses MetricSnapshot.source_event_ids — all event IDs in the window.
Per-type order.created IDs would require a snapshot schema extension.

Signal ID
----------
Deterministic: ``sig_order_volume_{outlet_id}_{window_start_utc}_{DETECTOR_VERSION}``
"""

from __future__ import annotations

from decimal import Decimal

from lossline_intelligence.aggregation.baseline import BaselineResult
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.detectors._common import (
    build_signal_id,
    deviation_ratio,
    orders_per_minute,
    quantize,
    ratio_severity,
    require_matching_outlet,
    robust_z_score,
)
from lossline_intelligence.models.signal import Signal, SignalType

MIN_ORDER_COUNT: int = 10
RATIO_THRESHOLD: Decimal = Decimal("1.30")
Z_SCORE_THRESHOLD: Decimal = Decimal("2.0")
SEVERITY_SCALE: Decimal = Decimal("4.0")
DETECTOR_VERSION: str = "order_volume_spike.v1"


def detect_order_volume_spike(
    snapshot: MetricSnapshot,
    baseline: BaselineResult,
    *,
    min_order_count: int = MIN_ORDER_COUNT,
    ratio_threshold: Decimal = RATIO_THRESHOLD,
    z_score_threshold: Decimal = Z_SCORE_THRESHOLD,
    severity_scale: Decimal = SEVERITY_SCALE,
) -> Signal | None:
    """Detect whether the current order rate is abnormally high."""
    require_matching_outlet(snapshot, baseline)

    if snapshot.order_count < min_order_count:
        return None

    if not snapshot.source_event_ids:
        return None

    baseline_median: Decimal | None = baseline.order_count.median
    if baseline_median is None:
        return None

    current_rate = orders_per_minute(snapshot.order_count, snapshot)
    current_count = Decimal(str(snapshot.order_count))

    if baseline_median == Decimal("0"):
        if current_count <= Decimal("0"):
            return None
        ratio = quantize(current_count)  # any positive count vs zero baseline
        ratio_met = True
        deviation = deviation_ratio(current_rate, Decimal("0"))
        baseline_rate = Decimal("0")
    else:
        baseline_rate = orders_per_minute(int(baseline_median), snapshot)
        ratio = quantize(current_rate / baseline_rate)
        ratio_met = ratio >= ratio_threshold
        deviation = deviation_ratio(current_rate, baseline_rate)

    if not ratio_met:
        return None

    z = robust_z_score(current_count, baseline_median, baseline.order_count.mad)
    if baseline_median != Decimal("0") and z < z_score_threshold:
        return None

    severity = ratio_severity(ratio, severity_scale)

    return Signal.model_validate(
        {
            "signal_id": build_signal_id("order_volume", snapshot, DETECTOR_VERSION),
            "outlet_id": snapshot.outlet_id,
            "signal_type": SignalType.ORDER_VOLUME_SPIKE,
            "severity": severity,
            "current_value": current_rate,
            "baseline_value": baseline_rate,
            "deviation_ratio": deviation,
            "unit": "orders_per_minute",
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "evidence_event_ids": snapshot.source_event_ids,
            "detector_version": DETECTOR_VERSION,
            "metadata": {
                "order_count": snapshot.order_count,
                "robust_z_score": str(z),
                "baseline_sample_count": baseline.order_count.sample_count,
                "baseline_sufficient": baseline.sufficient_history,
                "ratio_threshold": str(ratio_threshold),
                "z_score_threshold": str(z_score_threshold),
            },
        }
    )
