"""Tests for compute_baseline.

Coverage:
  1. Median baseline — odd number of snapshots
  2. Median baseline — even number of snapshots (avg of two middle values)
  3. Zero baseline — all metric values are zero
  4. Sparse optional metrics — no prep/handoff/review events in any window
  5. Insufficient history — sample_count < MIN_HISTORY_WINDOWS
  6. Another outlet rejected — foreign outlet snapshots never influence result
  7. Deterministic result — same input twice → identical output
  8. Identical historical values → zero MAD
  9. Single snapshot → MAD is None (not meaningful with one sample)
  10. Empty historical sequence → all medians None, sufficient_history False
  11. Mixed outlets → only matching outlet contributes
  12. Review rates — correct numerator/denominator handling
  13. Review rate when all review_count == 0 → no rate samples
  14. Configurable min_history_windows override
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.aggregation.baseline import (
    BASELINE_VERSION,
    MIN_HISTORY_WINDOWS,
    BaselineResult,
    MetricBaseline,
    compute_baseline,
)
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_OUTLET = "outlet_A"
_OTHER = "outlet_B"


def _snap(
    outlet_id: str = _OUTLET,
    order_count: int = 20,
    delivery_order_count: int = 10,
    cancelled_order_count: int = 2,
    cancellation_rate: str = "0.1000",
    avg_prep_minutes: str = "5.0000",
    p90_prep_minutes: str = "8.0000",
    avg_handoff_wait_minutes: str = "3.0000",
    review_count: int = 4,
    negative_review_count: int = 1,
    delay_review_count: int = 1,
    offset_hours: int = 0,
) -> MetricSnapshot:
    """Factory: create a MetricSnapshot with sensible defaults."""
    w_start = _W_START + timedelta(hours=offset_hours)
    w_end = w_start + timedelta(minutes=30)
    return MetricSnapshot.model_validate(
        {
            "outlet_id": outlet_id,
            "window_start": w_start,
            "window_end": w_end,
            "order_count": order_count,
            "delivery_order_count": delivery_order_count,
            "cancelled_order_count": cancelled_order_count,
            "cancellation_rate": Decimal(cancellation_rate),
            "avg_prep_minutes": Decimal(avg_prep_minutes),
            "p90_prep_minutes": Decimal(p90_prep_minutes),
            "prep_completed_count": 0,
            "avg_handoff_wait_minutes": Decimal(avg_handoff_wait_minutes),
            "handoff_completed_count": 0,
            "review_count": review_count,
            "negative_review_count": negative_review_count,
            "delay_review_count": delay_review_count,
            "delay_review_event_ids": (),
            "source_event_ids": (f"evt_{outlet_id}_{offset_hours}",),
        }
    )


def _baseline(snaps, *, outlet_id=_OUTLET, **kwargs) -> BaselineResult:
    return compute_baseline(snaps, outlet_id=outlet_id, **kwargs)


# ---------------------------------------------------------------------------
# 1. Median baseline — odd number of samples
# ---------------------------------------------------------------------------

def test_median_baseline_odd_samples() -> None:
    """3 snapshots: median of [0.05, 0.10, 0.15] → 0.10."""
    snaps = [
        _snap(cancellation_rate="0.0500", offset_hours=0),
        _snap(cancellation_rate="0.1000", offset_hours=1),
        _snap(cancellation_rate="0.1500", offset_hours=2),
    ]
    result = _baseline(snaps)

    assert result.cancellation_rate.median == Decimal("0.1000")
    assert result.cancellation_rate.sample_count == 3


# ---------------------------------------------------------------------------
# 2. Median baseline — even number of samples
# ---------------------------------------------------------------------------

def test_median_baseline_even_samples() -> None:
    """4 snapshots: median of [0.05, 0.10, 0.20, 0.30] → 0.15."""
    snaps = [
        _snap(cancellation_rate="0.0500", offset_hours=0),
        _snap(cancellation_rate="0.1000", offset_hours=1),
        _snap(cancellation_rate="0.2000", offset_hours=2),
        _snap(cancellation_rate="0.3000", offset_hours=3),
    ]
    result = _baseline(snaps)

    # statistics.median for 4 values: mean of 2nd and 3rd = (0.10+0.20)/2 = 0.15
    assert result.cancellation_rate.median == Decimal("0.1500")
    assert result.cancellation_rate.sample_count == 4
    assert result.sufficient_history is True


# ---------------------------------------------------------------------------
# 3. Zero baseline — all zeros
# ---------------------------------------------------------------------------

def test_zero_baseline_all_zeros() -> None:
    """All metrics zero → median is zero, not None."""
    snaps = [
        _snap(
            cancellation_rate="0.0000",
            avg_prep_minutes="0.0000",
            p90_prep_minutes="0.0000",
            avg_handoff_wait_minutes="0.0000",
            cancelled_order_count=0,
            order_count=10,
            delivery_order_count=5,
            review_count=0,
            negative_review_count=0,
            delay_review_count=0,
            offset_hours=i,
        )
        for i in range(4)
    ]
    result = _baseline(snaps)

    assert result.cancellation_rate.median == Decimal("0.0000")
    assert result.avg_prep_minutes.median == Decimal("0.0000")
    assert result.avg_handoff_wait_minutes.median == Decimal("0.0000")
    assert result.sufficient_history is True


# ---------------------------------------------------------------------------
# 4. Missing optional metrics (no prep/handoff events → zero values)
# ---------------------------------------------------------------------------

def test_sparse_optional_metrics_produce_zero_median() -> None:
    """Windows with no prep/handoff events have 0 values → median is 0."""
    snaps = [
        _snap(
            avg_prep_minutes="0.0000",
            p90_prep_minutes="0.0000",
            avg_handoff_wait_minutes="0.0000",
            offset_hours=i,
        )
        for i in range(4)
    ]
    result = _baseline(snaps)

    assert result.avg_prep_minutes.median == Decimal("0.0000")
    assert result.avg_prep_minutes.sample_count == 4
    assert result.p90_prep_minutes.median == Decimal("0.0000")
    assert result.avg_handoff_wait_minutes.median == Decimal("0.0000")


# ---------------------------------------------------------------------------
# 5. Insufficient history
# ---------------------------------------------------------------------------

def test_insufficient_history_flag() -> None:
    """3 snapshots < MIN_HISTORY_WINDOWS(4) → sufficient_history False."""
    snaps = [_snap(offset_hours=i) for i in range(MIN_HISTORY_WINDOWS - 1)]
    result = _baseline(snaps)

    assert result.sufficient_history is False
    assert result.sample_count == MIN_HISTORY_WINDOWS - 1
    # Median is still computed when samples exist
    assert result.cancellation_rate.median is not None


def test_exactly_min_history_is_sufficient() -> None:
    """sample_count == MIN_HISTORY_WINDOWS → sufficient_history True."""
    snaps = [_snap(offset_hours=i) for i in range(MIN_HISTORY_WINDOWS)]
    result = _baseline(snaps)

    assert result.sufficient_history is True
    assert result.sample_count == MIN_HISTORY_WINDOWS


# ---------------------------------------------------------------------------
# 6. Another outlet is rejected/excluded
# ---------------------------------------------------------------------------

def test_foreign_outlet_snapshots_are_ignored() -> None:
    """Snapshots for outlet_B must never influence outlet_A's baseline."""
    own_snaps = [_snap(outlet_id=_OUTLET, offset_hours=i) for i in range(4)]
    foreign_snaps = [
        _snap(
            outlet_id=_OTHER,
            cancellation_rate="0.9000",  # would badly skew the median
            offset_hours=i,
        )
        for i in range(10)
    ]
    result = _baseline(own_snaps + foreign_snaps)

    assert result.outlet_id == _OUTLET
    assert result.sample_count == 4          # only own snapshots counted
    # Median must not be influenced by the 0.90 foreign rate
    assert result.cancellation_rate.median is not None
    assert result.cancellation_rate.median < Decimal("0.5000")


# ---------------------------------------------------------------------------
# 7. Deterministic result
# ---------------------------------------------------------------------------

def test_deterministic_result() -> None:
    """Same input twice → identical BaselineResult."""
    snaps = [_snap(offset_hours=i) for i in range(5)]
    r1 = _baseline(snaps)
    r2 = _baseline(snaps)
    assert r1 == r2


# ---------------------------------------------------------------------------
# 8. Identical historical values → zero MAD
# ---------------------------------------------------------------------------

def test_identical_values_produce_zero_mad() -> None:
    """When all samples have the same value, MAD must be zero (not None)."""
    snaps = [_snap(cancellation_rate="0.0800", offset_hours=i) for i in range(5)]
    result = _baseline(snaps)

    assert result.cancellation_rate.median == Decimal("0.0800")
    assert result.cancellation_rate.mad == Decimal("0.0000")


# ---------------------------------------------------------------------------
# 9. Single snapshot → MAD is None
# ---------------------------------------------------------------------------

def test_single_snapshot_mad_is_none() -> None:
    """One sample is not enough to compute MAD."""
    snaps = [_snap(offset_hours=0)]
    result = _baseline(snaps)

    assert result.sample_count == 1
    assert result.cancellation_rate.median is not None
    assert result.cancellation_rate.mad is None


# ---------------------------------------------------------------------------
# 10. Empty historical sequence
# ---------------------------------------------------------------------------

def test_empty_history_returns_none_medians() -> None:
    """No snapshots → all medians None, MADs None, counts 0."""
    result = _baseline([])

    assert result.sample_count == 0
    assert result.sufficient_history is False
    assert result.outlet_id == _OUTLET
    assert result.baseline_version == BASELINE_VERSION

    for field_name in (
        "order_count",
        "cancellation_rate",
        "avg_prep_minutes",
        "p90_prep_minutes",
        "avg_handoff_wait_minutes",
        "negative_review_rate",
        "delay_review_rate",
    ):
        mb: MetricBaseline = getattr(result, field_name)
        assert mb.median is None, f"{field_name}.median should be None"
        assert mb.mad is None, f"{field_name}.mad should be None"
        assert mb.sample_count == 0, f"{field_name}.sample_count should be 0"


# ---------------------------------------------------------------------------
# 11. Mixed outlets — only matching outlet contributes
# ---------------------------------------------------------------------------

def test_mixed_outlets_only_own_contribute() -> None:
    """When passed a mixed sequence, only outlet_A snapshots contribute."""
    snaps = (
        [_snap(outlet_id=_OUTLET, offset_hours=i) for i in range(4)]
        + [_snap(outlet_id=_OTHER, offset_hours=i) for i in range(4)]
    )
    result_a = _baseline(snaps, outlet_id=_OUTLET)
    result_b = _baseline(snaps, outlet_id=_OTHER)

    assert result_a.sample_count == 4
    assert result_b.sample_count == 4
    # Both use the same factory defaults so medians should be equal
    assert result_a.cancellation_rate.median == result_b.cancellation_rate.median


# ---------------------------------------------------------------------------
# 12. Review rates computed correctly
# ---------------------------------------------------------------------------

def test_negative_review_rate_correct() -> None:
    """negative_review_rate = median(negative_count / review_count per window)."""
    # Window 1: 1/4 = 0.25; Window 2: 2/4 = 0.50; Window 3: 3/4 = 0.75
    # median of [0.25, 0.50, 0.75] = 0.50
    snaps = [
        _snap(review_count=4, negative_review_count=1, delay_review_count=0, offset_hours=0),
        _snap(review_count=4, negative_review_count=2, delay_review_count=0, offset_hours=1),
        _snap(review_count=4, negative_review_count=3, delay_review_count=0, offset_hours=2),
    ]
    result = _baseline(snaps)

    assert result.negative_review_rate.median == Decimal("0.5000")
    assert result.negative_review_rate.sample_count == 3


# ---------------------------------------------------------------------------
# 13. Review rate when all review_count == 0 → no samples
# ---------------------------------------------------------------------------

def test_review_rate_with_no_reviews_has_no_samples() -> None:
    """Windows with zero reviews produce no rate sample → median None."""
    snaps = [
        _snap(review_count=0, negative_review_count=0, delay_review_count=0, offset_hours=i)
        for i in range(4)
    ]
    result = _baseline(snaps)

    assert result.negative_review_rate.median is None
    assert result.negative_review_rate.sample_count == 0
    assert result.delay_review_rate.median is None


# ---------------------------------------------------------------------------
# 14. Configurable min_history_windows
# ---------------------------------------------------------------------------

def test_configurable_min_history_override() -> None:
    """Caller can lower the threshold; 2 snaps suffice when min=2."""
    snaps = [_snap(offset_hours=i) for i in range(2)]
    result = _baseline(snaps, min_history_windows=2)

    assert result.sufficient_history is True
    assert result.sample_count == 2


def test_configurable_min_history_higher() -> None:
    """Caller can raise the threshold; 4 snaps insufficient when min=10."""
    snaps = [_snap(offset_hours=i) for i in range(4)]
    result = _baseline(snaps, min_history_windows=10)

    assert result.sufficient_history is False
    assert result.sample_count == 4


# ---------------------------------------------------------------------------
# 15. MAD with spread values
# ---------------------------------------------------------------------------

def test_mad_reflects_spread() -> None:
    """Wider spread → larger MAD."""
    tight_snaps = [
        _snap(cancellation_rate="0.0900", offset_hours=0),
        _snap(cancellation_rate="0.1000", offset_hours=1),
        _snap(cancellation_rate="0.1100", offset_hours=2),
        _snap(cancellation_rate="0.1000", offset_hours=3),
    ]
    wide_snaps = [
        _snap(cancellation_rate="0.0100", offset_hours=0),
        _snap(cancellation_rate="0.1000", offset_hours=1),
        _snap(cancellation_rate="0.3000", offset_hours=2),
        _snap(cancellation_rate="0.5000", offset_hours=3),
    ]
    tight = _baseline(tight_snaps)
    wide = _baseline(wide_snaps)

    assert tight.cancellation_rate.mad is not None
    assert wide.cancellation_rate.mad is not None
    assert wide.cancellation_rate.mad > tight.cancellation_rate.mad


# ---------------------------------------------------------------------------
# 16. Invalid outlet_id raises
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["", "   "])
def test_empty_outlet_id_raises(bad_id: str) -> None:
    with pytest.raises(ValueError, match="outlet_id"):
        compute_baseline([], outlet_id=bad_id)


# ---------------------------------------------------------------------------
# 17. Order count baseline
# ---------------------------------------------------------------------------

def test_order_count_baseline() -> None:
    """order_count median uses integer→Decimal conversion correctly."""
    snaps = [
        _snap(order_count=10, offset_hours=0),
        _snap(order_count=20, offset_hours=1),
        _snap(order_count=30, offset_hours=2),
    ]
    result = _baseline(snaps)

    assert result.order_count.median == Decimal("20.0000")
    assert result.order_count.sample_count == 3
