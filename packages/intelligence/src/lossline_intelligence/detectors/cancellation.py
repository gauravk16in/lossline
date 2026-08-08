"""CANCELLATION_SPIKE deterministic detector.

Responsibility
--------------
Given a current MetricSnapshot and a BaselineResult for the same outlet
and window, decide whether the cancellation rate constitutes an anomalous
spike and, if so, emit a Signal.

What this module does NOT do
-----------------------------
- No LLM calls, no LangGraph, no I/O, no database, no Redis.
- No baseline computation — that is the caller's responsibility.
- No correlation with other signal types.

Detection Rule (CONFIG_DEFAULT — FINAL_IMPLEMENTATION_PLAN §Detector Specs)
---------------------------------------------------------------------------
Fire only when ALL of the following conditions hold:

  1. Sample sufficiency:
       current.order_count >= MIN_ORDER_COUNT

  2. Ratio threshold:
       current_rate >= baseline_rate * RATIO_THRESHOLD   (default: 2.0×)

  3. Absolute gap threshold:
       current_rate - baseline_rate >= ABSOLUTE_GAP_THRESHOLD  (default: 0.05)

Condition (3) prevents the rule from firing on trivially small baseline
rates (e.g. baseline=0.001, current=0.002 — technically 2× but only 0.1 pp).

Zero-baseline handling
-----------------------
When baseline_rate is zero:
  - Condition (2) is treated as satisfied only when current_rate > 0.
  - deviation_ratio is set to Decimal("0") to avoid division-by-zero.
  - This is a named, explicit path — never a silent NaN or inf.

Severity formula (deterministic, monotonic)
--------------------------------------------
severity = min(1.0, excess_ratio / SEVERITY_SCALE)

where:
  excess_ratio = current_rate / baseline_rate  (or current_rate if baseline=0)
  SEVERITY_SCALE = 4.0  (CONFIG_DEFAULT: ratio that maps to severity=1.0)

This produces:
  2.0× → 0.50   (LOW–MEDIUM boundary)
  3.0× → 0.75   (HIGH)
  4.0× → 1.0    (capped)
  >4.0× → 1.0   (capped)

Evidence
---------
Uses MetricSnapshot.source_event_ids — all event IDs that contributed to the
window.  This is the finest-grained evidence the current snapshot contract
exposes.  A future schema improvement (per-event-type ID tracking) would
allow restricting to just order.created / order.cancelled IDs.

Signal ID
----------
Deterministic: ``sig_cancel_{outlet_id}_{window_start_utc}_{DETECTOR_VERSION}``
Same outlet + same window + same version always produces the same signal_id
(idempotency-friendly for outbox/replay).
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP

from lossline_intelligence.aggregation.baseline import BaselineResult
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.models.signal import Signal, SignalType

# ---------------------------------------------------------------------------
# Configuration defaults (CONFIG_DEFAULT — not business facts)
# ---------------------------------------------------------------------------

#: Minimum orders in the current window before the detector fires.
#: Guards against noisy low-volume windows.
MIN_ORDER_COUNT: int = 10

#: Current rate must be at least this many times the baseline rate.
RATIO_THRESHOLD: Decimal = Decimal("2.0")

#: Current rate must exceed baseline by at least this many percentage points.
ABSOLUTE_GAP_THRESHOLD: Decimal = Decimal("0.05")

#: The excess ratio that maps to severity = 1.0 (cap).
SEVERITY_SCALE: Decimal = Decimal("4.0")

#: Versioned detector identifier embedded in every Signal.
DETECTOR_VERSION: str = "cancellation_spike.v2"

#: Decimal rounding precision for Decimal outputs.
_DP = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_cancellation_spike(
    snapshot: MetricSnapshot,
    baseline: BaselineResult,
    *,
    min_order_count: int = MIN_ORDER_COUNT,
    ratio_threshold: Decimal = RATIO_THRESHOLD,
    absolute_gap_threshold: Decimal = ABSOLUTE_GAP_THRESHOLD,
    severity_scale: Decimal = SEVERITY_SCALE,
) -> Signal | None:
    """Detect whether the current cancellation rate is anomalously high.

    Parameters
    ----------
    snapshot:
        Current-window MetricSnapshot.  Must belong to the same outlet as
        ``baseline``.
    baseline:
        BaselineResult produced by ``compute_baseline`` for the same outlet.
    min_order_count:
        Minimum number of orders required before the detector fires.
        Overrides the module CONFIG_DEFAULT.
    ratio_threshold:
        Minimum current/baseline ratio to fire.  Overrides CONFIG_DEFAULT.
    absolute_gap_threshold:
        Minimum absolute difference (percentage points as a fraction) to fire.
        Overrides CONFIG_DEFAULT.
    severity_scale:
        The excess ratio that saturates severity at 1.0.
        Overrides CONFIG_DEFAULT.

    Returns
    -------
    Signal
        If all trigger conditions are met.
    None
        If any condition fails, or if the baseline is insufficient and
        baseline_rate is None (abstain rather than fabricate).

    Raises
    ------
    ValueError
        If snapshot.outlet_id != baseline.outlet_id (programming error,
        not a data-quality issue).
    """
    if snapshot.outlet_id != baseline.outlet_id:
        raise ValueError(
            f"outlet mismatch: snapshot.outlet_id={snapshot.outlet_id!r} "
            f"!= baseline.outlet_id={baseline.outlet_id!r}"
        )

    # --- Guard: insufficient sample size in current window -------------------
    if snapshot.order_count < min_order_count:
        return None

    # --- Guard: no evidence IDs to attach (Signal requires ≥1) ---------------
    if not snapshot.source_event_ids:
        return None

    # --- Retrieve baseline rate; abstain if never computed -------------------
    baseline_rate: Decimal | None = baseline.cancellation_rate.median
    current_rate: Decimal = snapshot.cancellation_rate

    # When baseline has insufficient history (median is None), abstain rather
    # than invent a comparison point.
    if baseline_rate is None:
        return None

    # --- Condition 2: ratio check --------------------------------------------
    #   Special case: baseline_rate == 0
    #   The rule fires only if current_rate > 0 (any non-zero rate > 0× = ∞×).
    if baseline_rate == Decimal("0"):
        ratio_met = current_rate > Decimal("0")
        # deviation_ratio is undefined when baseline=0; use 0 to avoid inf.
        deviation_ratio = Decimal("0")
        # For severity: use current_rate itself as the "excess" signal,
        # normalised by the absolute gap threshold.
        if ratio_met and current_rate >= absolute_gap_threshold:
            severity_raw = float(current_rate / absolute_gap_threshold / severity_scale)
            severity = min(1.0, round(severity_raw, 4))
        else:
            return None
    else:
        # Normal path: baseline_rate > 0
        ratio = (current_rate / baseline_rate).quantize(_DP, rounding=ROUND_HALF_UP)
        ratio_met = ratio >= ratio_threshold

        absolute_gap = (current_rate - baseline_rate).quantize(_DP, rounding=ROUND_HALF_UP)
        gap_met = absolute_gap >= absolute_gap_threshold

        if not (ratio_met and gap_met):
            return None

        deviation_ratio = (
            (current_rate - baseline_rate) / baseline_rate
        ).quantize(_DP, rounding=ROUND_HALF_UP)

        # Severity: min(1.0, ratio / severity_scale)
        severity = float(
            min(Decimal("1.0"), (ratio / severity_scale).quantize(
                _DP, rounding=ROUND_HALF_UP
            ))
        )

    # --- Build deterministic signal_id ---------------------------------------
    window_tag = snapshot.window_start.astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    signal_id = (
        f"sig_cancel_{snapshot.outlet_id}_{window_tag}_{DETECTOR_VERSION}"
    )

    return Signal.model_validate(
        {
            "signal_id": signal_id,
            "outlet_id": snapshot.outlet_id,
            "signal_type": SignalType.CANCELLATION_SPIKE,
            "severity": severity,
            "current_value": current_rate,
            "baseline_value": baseline_rate,
            "deviation_ratio": deviation_ratio,
            "unit": "cancellation_rate",
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "evidence_event_ids": snapshot.source_event_ids,
            "detector_version": DETECTOR_VERSION,
            "metadata": {
                "order_count": snapshot.order_count,
                "cancelled_order_count": snapshot.cancelled_order_count,
                "baseline_sample_count": baseline.cancellation_rate.sample_count,
                "baseline_sufficient": baseline.sufficient_history,
                "ratio_threshold": str(ratio_threshold),
                "absolute_gap_threshold": str(absolute_gap_threshold),
            },
        }
    )
