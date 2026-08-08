"""Tests for the CANCELLATION_SPIKE detector (detectors/cancellation.py).

Tests use MetricSnapshot + BaselineResult directly — no database, no Redis,
no LangGraph, no LLM.

Coverage:
  1.  Clear spike fires
  2.  Normal rate does not fire
  3.  2× ratio met but < 5pp absolute gap → no fire
  4.  > 5pp gap but < 2× ratio → no fire
  5.  Insufficient sample (order_count < MIN_ORDER_COUNT) → no fire
  6a. Zero baseline, current > 0 and meets gap → fires
  6b. Zero baseline, current = 0 → no fire
  6c. Zero baseline, current > 0 but below absolute gap → no fire
  7.  Severity bounded to [0, 1]
  8.  Deterministic signal ID (same inputs → same id)
  9.  Correct outlet_id, window, unit on emitted Signal
  10. Repeated invocation produces equivalent output (idempotency)
  11. Outlet mismatch raises ValueError
  12. No source_event_ids → no fire (Signal requires ≥1)
  13. Insufficient baseline history → no fire (median is None)
  14. Severity increases monotonically with ratio
  15. Configurable threshold overrides work
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.aggregation.baseline import (
    BaselineResult,
    MetricBaseline,
    BASELINE_VERSION,
)
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.detectors.cancellation import (
    DETECTOR_VERSION,
    MIN_ORDER_COUNT,
    RATIO_THRESHOLD,
    ABSOLUTE_GAP_THRESHOLD,
    detect_cancellation_spike,
)
from lossline_intelligence.models.signal import SignalType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_W_END = _W_START + timedelta(minutes=30)
_OUTLET = "outlet_test"


def _snap(
    outlet_id: str = _OUTLET,
    order_count: int = 20,
    cancelled_order_count: int = 4,
    cancellation_rate: str = "0.2000",
    source_event_ids: tuple[str, ...] = ("evt_001", "evt_002", "evt_003"),
) -> MetricSnapshot:
    """Factory: create a MetricSnapshot with the given cancellation figures."""
    # cancelled must not exceed order_count
    actual_cancelled = min(cancelled_order_count, order_count)
    return MetricSnapshot.model_validate(
        {
            "outlet_id": outlet_id,
            "window_start": _W_START,
            "window_end": _W_END,
            "order_count": order_count,
            "delivery_order_count": 0,
            "cancelled_order_count": actual_cancelled,
            "cancellation_rate": Decimal(cancellation_rate),
            "avg_prep_minutes": Decimal("0"),
            "p90_prep_minutes": Decimal("0"),
            "prep_completed_count": 0,
            "avg_handoff_wait_minutes": Decimal("0"),
            "handoff_completed_count": 0,
            "review_count": 0,
            "negative_review_count": 0,
            "delay_review_count": 0,
            "delay_review_event_ids": (),
            "source_event_ids": source_event_ids,
        }
    )


def _mb(median: str | None, *, sample_count: int = 5) -> MetricBaseline:
    """Build a MetricBaseline with given median (as string) and default MAD."""
    med = Decimal(median) if median is not None else None
    mad = Decimal("0.0050") if med is not None else None
    return MetricBaseline(median=med, mad=mad, sample_count=sample_count)


def _empty_mb() -> MetricBaseline:
    return MetricBaseline(median=None, mad=None, sample_count=0)


def _baseline(
    outlet_id: str = _OUTLET,
    cancel_median: str | None = "0.0800",
    sufficient: bool = True,
) -> BaselineResult:
    """Factory: create a BaselineResult with a given cancellation_rate median."""
    mb = _mb(cancel_median) if cancel_median is not None else _empty_mb()
    empty = _empty_mb()
    return BaselineResult(
        outlet_id=outlet_id,
        sample_count=mb.sample_count,
        sufficient_history=sufficient,
        baseline_version=BASELINE_VERSION,
        order_count=_mb("18.0000"),
        cancellation_rate=mb,
        avg_prep_minutes=empty,
        p90_prep_minutes=empty,
        avg_handoff_wait_minutes=empty,
        negative_review_rate=empty,
        delay_review_rate=empty,
    )


def _detect(
    snap: MetricSnapshot | None = None,
    base: BaselineResult | None = None,
    **kwargs,
):
    s = snap if snap is not None else _snap()
    b = base if base is not None else _baseline()
    return detect_cancellation_spike(s, b, **kwargs)


# ---------------------------------------------------------------------------
# 1. Clear spike fires
# ---------------------------------------------------------------------------

def test_clear_spike_fires() -> None:
    """current=0.20, baseline=0.08 → ratio=2.5×, gap=0.12 → fires."""
    snap = _snap(order_count=20, cancellation_rate="0.2000")
    base = _baseline(cancel_median="0.0800")
    result = _detect(snap, base)

    assert result is not None
    assert result.signal_type is SignalType.CANCELLATION_SPIKE
    assert result.outlet_id == _OUTLET
    assert result.current_value == Decimal("0.2000")
    assert result.baseline_value == Decimal("0.0800")


# ---------------------------------------------------------------------------
# 2. Normal rate does not fire
# ---------------------------------------------------------------------------

def test_normal_rate_does_not_fire() -> None:
    """current=0.09, baseline=0.08 → ratio=1.125× < 2× → no fire."""
    snap = _snap(order_count=20, cancellation_rate="0.0900")
    base = _baseline(cancel_median="0.0800")
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 3. 2× ratio met but < 5pp gap → no fire
# ---------------------------------------------------------------------------

def test_ratio_met_but_gap_too_small_does_not_fire() -> None:
    """baseline=0.02, current=0.04 → ratio=2.0× ✓ but gap=0.02 < 0.05 → no fire."""
    snap = _snap(order_count=20, cancellation_rate="0.0400")
    base = _baseline(cancel_median="0.0200")
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 4. > 5pp gap but < 2× ratio → no fire
# ---------------------------------------------------------------------------

def test_gap_met_but_ratio_too_small_does_not_fire() -> None:
    """baseline=0.50, current=0.56 → gap=0.06 ✓ but ratio=1.12× < 2× → no fire."""
    snap = _snap(order_count=20, cancellation_rate="0.5600", cancelled_order_count=11)
    base = _baseline(cancel_median="0.5000")
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 5. Insufficient sample (order_count < MIN_ORDER_COUNT) → no fire
# ---------------------------------------------------------------------------

def test_insufficient_order_count_does_not_fire() -> None:
    """order_count = MIN_ORDER_COUNT - 1 → guard fails → no fire."""
    snap = _snap(order_count=MIN_ORDER_COUNT - 1, cancellation_rate="0.5000",
                 cancelled_order_count=MIN_ORDER_COUNT - 1)
    base = _baseline(cancel_median="0.0800")
    assert _detect(snap, base) is None


def test_exactly_min_order_count_allows_fire() -> None:
    """order_count == MIN_ORDER_COUNT → guard passes (boundary condition)."""
    snap = _snap(
        order_count=MIN_ORDER_COUNT,
        cancelled_order_count=MIN_ORDER_COUNT,
        cancellation_rate="0.2000",
    )
    base = _baseline(cancel_median="0.0800")
    assert _detect(snap, base) is not None


# ---------------------------------------------------------------------------
# 6. Zero baseline behaviour
# ---------------------------------------------------------------------------

def test_zero_baseline_fires_when_current_meets_gap() -> None:
    """baseline=0.00, current=0.10 ≥ 0.05 → fires."""
    snap = _snap(order_count=20, cancellation_rate="0.1000")
    base = _baseline(cancel_median="0.0000")
    result = _detect(snap, base)

    assert result is not None
    assert result.baseline_value == Decimal("0.0000")
    # deviation_ratio must be 0 (not NaN / inf) when baseline=0
    assert result.deviation_ratio == Decimal("0")
    assert result.severity >= 0.0


def test_zero_baseline_zero_current_does_not_fire() -> None:
    """baseline=0.00, current=0.00 → no spike."""
    snap = _snap(order_count=20, cancellation_rate="0.0000", cancelled_order_count=0)
    base = _baseline(cancel_median="0.0000")
    assert _detect(snap, base) is None


def test_zero_baseline_current_below_gap_does_not_fire() -> None:
    """baseline=0.00, current=0.03 < 0.05 → no fire (gap not met)."""
    snap = _snap(order_count=20, cancellation_rate="0.0300", cancelled_order_count=1)
    base = _baseline(cancel_median="0.0000")
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 7. Severity bounded to [0, 1]
# ---------------------------------------------------------------------------

def test_severity_bounded() -> None:
    """Extreme ratio should not exceed 1.0."""
    snap = _snap(order_count=20, cancellation_rate="0.9000", cancelled_order_count=18)
    base = _baseline(cancel_median="0.0100")
    result = _detect(snap, base)

    assert result is not None
    assert 0.0 <= result.severity <= 1.0


def test_severity_at_2x_ratio_is_0_5() -> None:
    """Exactly 2× ratio → severity = 2.0 / SEVERITY_SCALE(4.0) = 0.5."""
    snap = _snap(order_count=20, cancellation_rate="0.2000")   # 2× of 0.10
    base = _baseline(cancel_median="0.1000")
    result = _detect(snap, base)

    assert result is not None
    assert abs(result.severity - 0.5) < 0.01


# ---------------------------------------------------------------------------
# 8. Deterministic signal ID
# ---------------------------------------------------------------------------

def test_deterministic_signal_id() -> None:
    """Same inputs always produce the same signal_id."""
    snap = _snap()
    base = _baseline()
    r1 = detect_cancellation_spike(snap, base)
    r2 = detect_cancellation_spike(snap, base)

    assert r1 is not None and r2 is not None
    assert r1.signal_id == r2.signal_id


def test_signal_id_contains_outlet_and_window() -> None:
    """signal_id encodes outlet_id and window_start (UTC) for traceability."""
    result = _detect()
    assert result is not None
    assert _OUTLET in result.signal_id
    assert "20260808T120000Z" in result.signal_id
    assert DETECTOR_VERSION in result.signal_id


# ---------------------------------------------------------------------------
# 9. Correct outlet, window, unit on emitted Signal
# ---------------------------------------------------------------------------

def test_signal_fields_correct() -> None:
    result = _detect()
    assert result is not None

    assert result.outlet_id == _OUTLET
    assert result.window_start == _W_START
    assert result.window_end == _W_END
    assert result.unit == "cancellation_rate"
    assert result.detector_version == DETECTOR_VERSION
    assert result.signal_type is SignalType.CANCELLATION_SPIKE


def test_evidence_event_ids_come_from_snapshot() -> None:
    """evidence_event_ids must be the snapshot's source_event_ids."""
    ids = ("e1", "e2", "e3", "e4")
    snap = _snap(source_event_ids=ids)
    result = _detect(snap)

    assert result is not None
    assert set(result.evidence_event_ids) == set(ids)


# ---------------------------------------------------------------------------
# 10. Repeated invocation → equivalent output
# ---------------------------------------------------------------------------

def test_repeated_invocation_produces_equivalent_output() -> None:
    snap = _snap()
    base = _baseline()
    results = [detect_cancellation_spike(snap, base) for _ in range(5)]
    assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# 11. Outlet mismatch raises ValueError
# ---------------------------------------------------------------------------

def test_outlet_mismatch_raises() -> None:
    snap = _snap(outlet_id="outlet_X")
    base = _baseline(outlet_id="outlet_Y")
    with pytest.raises(ValueError, match="outlet"):
        detect_cancellation_spike(snap, base)


# ---------------------------------------------------------------------------
# 12. No source_event_ids → no fire
# ---------------------------------------------------------------------------

def test_no_source_event_ids_does_not_fire() -> None:
    """Signal requires ≥1 evidence ID; empty source_event_ids → abstain."""
    snap = _snap(source_event_ids=())
    base = _baseline()
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 13. Insufficient baseline history → no fire (median is None)
# ---------------------------------------------------------------------------

def test_none_baseline_median_does_not_fire() -> None:
    """baseline.cancellation_rate.median is None → abstain."""
    snap = _snap()
    base = _baseline(cancel_median=None)
    assert _detect(snap, base) is None


# ---------------------------------------------------------------------------
# 14. Severity increases monotonically with ratio
# ---------------------------------------------------------------------------

def test_severity_monotonic_with_ratio() -> None:
    """Higher current_rate (given same baseline) → higher or equal severity."""
    base = _baseline(cancel_median="0.0800")
    rates = ["0.1600", "0.2400", "0.3200", "0.4000"]  # 2×, 3×, 4×, 5×
    severities = []
    for rate in rates:
        snap = _snap(order_count=20, cancellation_rate=rate, cancelled_order_count=20)
        r = detect_cancellation_spike(snap, base)
        assert r is not None
        severities.append(r.severity)

    for i in range(len(severities) - 1):
        assert severities[i] <= severities[i + 1], (
            f"severity not monotonic at index {i}: {severities}"
        )


# ---------------------------------------------------------------------------
# 15. Configurable threshold overrides
# ---------------------------------------------------------------------------

def test_custom_ratio_threshold_respected() -> None:
    """With ratio_threshold=1.5, a 1.6× ratio should fire."""
    snap = _snap(order_count=20, cancellation_rate="0.1600")  # 1.6× of 0.10
    base = _baseline(cancel_median="0.1000")

    # Default 2× threshold → should NOT fire
    assert _detect(snap, base) is None

    # Lowered to 1.5× → should fire (gap = 0.06 > 0.05 ✓, ratio = 1.6 > 1.5 ✓)
    result = detect_cancellation_spike(snap, base, ratio_threshold=Decimal("1.5"))
    assert result is not None


def test_custom_absolute_gap_threshold_respected() -> None:
    """With gap_threshold=0.01, a 0.02 gap (with 2× ratio) should fire."""
    # baseline=0.02, current=0.04 → 2× ratio ✓, gap=0.02 which is < default 0.05
    snap = _snap(order_count=20, cancellation_rate="0.0400", cancelled_order_count=1)
    base = _baseline(cancel_median="0.0200")

    # Default gap 0.05 → no fire
    assert _detect(snap, base) is None

    # Lowered gap to 0.01 → fires (gap=0.02 > 0.01 ✓)
    result = detect_cancellation_spike(
        snap, base, absolute_gap_threshold=Decimal("0.01")
    )
    assert result is not None


def test_custom_min_order_count_respected() -> None:
    """With min_order_count=5, a window of 8 orders should be eligible."""
    snap = _snap(order_count=8, cancellation_rate="0.2000", cancelled_order_count=8)
    base = _baseline(cancel_median="0.0800")

    # Default MIN=10 → no fire
    assert _detect(snap, base) is None

    # Lowered to 5 → fires
    result = detect_cancellation_spike(snap, base, min_order_count=5)
    assert result is not None
