"""DELAY_REVIEW_SPIKE deterministic detector.

Responsibility
--------------
Given a current MetricSnapshot and a BaselineResult for the same outlet
and window, decide whether there is a significant cluster of low-rated
reviews mentioning delay-related terms.

Classification is delegated entirely to the snapshot builder — this detector
does NOT call an LLM and does NOT re-run keyword matching.

Detection Rule (CONFIG_DEFAULT — FINAL_IMPLEMENTATION_PLAN §Detector Specs)
---------------------------------------------------------------------------
Fire only when:

  snapshot.delay_review_count >= MIN_QUALIFYING_REVIEWS   (default: 2)

Each qualifying review is a rating ≤ 2 whose text contains a configured
delay keyword (same rules as metric_snapshot_builder).

Severity formula (deterministic, monotonic)
--------------------------------------------
severity = min(1.0, delay_review_count / SEVERITY_SCALE)

where SEVERITY_SCALE = 8.0 maps eight qualifying reviews to severity 1.0.

Evidence
---------
Uses MetricSnapshot.delay_review_event_ids — the review event IDs that
contributed to delay_review_count during aggregation.

Signal ID
----------
Deterministic: ``sig_delay_review_{outlet_id}_{window_start_utc}_{DETECTOR_VERSION}``
"""

from __future__ import annotations

from decimal import Decimal

from lossline_intelligence.aggregation.baseline import BaselineResult
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.detectors._common import (
    build_signal_id,
    quantize,
    require_matching_outlet,
)
from lossline_intelligence.models.signal import Signal, SignalType

MIN_QUALIFYING_REVIEWS: int = 2
SEVERITY_SCALE: Decimal = Decimal("8.0")
DETECTOR_VERSION: str = "delay_review_spike.v1"


def detect_delay_review_spike(
    snapshot: MetricSnapshot,
    baseline: BaselineResult,
    *,
    min_qualifying_reviews: int = MIN_QUALIFYING_REVIEWS,
    severity_scale: Decimal = SEVERITY_SCALE,
) -> Signal | None:
    """Detect a cluster of negative, delay-mentioning reviews."""
    require_matching_outlet(snapshot, baseline)

    count = snapshot.delay_review_count
    if count < min_qualifying_reviews:
        return None

    evidence_ids = snapshot.delay_review_event_ids
    if not evidence_ids:
        return None

    current_value = Decimal(str(count))
    baseline_rate = baseline.delay_review_rate.median
    baseline_value = baseline_rate if baseline_rate is not None else Decimal("0")

    severity = float(
        min(Decimal("1.0"), quantize(current_value / severity_scale))
    )

    return Signal.model_validate(
        {
            "signal_id": build_signal_id("delay_review", snapshot, DETECTOR_VERSION),
            "outlet_id": snapshot.outlet_id,
            "signal_type": SignalType.DELAY_REVIEW_SPIKE,
            "severity": severity,
            "current_value": current_value,
            "baseline_value": baseline_value,
            "deviation_ratio": quantize(current_value - baseline_value),
            "unit": "qualifying_reviews",
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "evidence_event_ids": evidence_ids,
            "detector_version": DETECTOR_VERSION,
            "metadata": {
                "delay_review_count": count,
                "review_count": snapshot.review_count,
                "baseline_delay_review_rate": str(baseline_rate)
                if baseline_rate is not None
                else None,
                "baseline_sample_count": baseline.delay_review_rate.sample_count,
                "baseline_sufficient": baseline.sufficient_history,
                "min_qualifying_reviews": min_qualifying_reviews,
            },
        }
    )
