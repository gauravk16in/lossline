"""Tests for ORDER_VOLUME_SPIKE detector (detectors/order_volume.py)."""

from decimal import Decimal

import pytest

from lossline_intelligence.detectors.order_volume import (
    DETECTOR_VERSION,
    MIN_ORDER_COUNT,
    RATIO_THRESHOLD,
    Z_SCORE_THRESHOLD,
    detect_order_volume_spike,
)
from lossline_intelligence.models.signal import SignalType
from .fixtures.detector_fixtures import (
    OUTLET,
    W_END,
    W_START,
    baseline,
    mb,
    snap,
)


def test_obvious_spike_fires() -> None:
    """39 orders vs baseline 18 → ratio ~2.17×, z-score well above 2."""
    result = detect_order_volume_spike(
        snap(order_count=39),
        baseline(order_count=mb("18.0000", mad="1.0000")),
    )
    assert result is not None
    assert result.signal_type is SignalType.ORDER_VOLUME_SPIKE
    assert result.outlet_id == OUTLET
    assert result.unit == "orders_per_minute"


def test_just_below_ratio_threshold_does_not_fire() -> None:
    """23/18 ≈ 1.28× < 1.30 → no fire."""
    assert (
        detect_order_volume_spike(
            snap(order_count=23),
            baseline(order_count=mb("18.0000", mad="1.0000")),
        )
        is None
    )


def test_ratio_met_but_z_score_too_low_does_not_fire() -> None:
    """High MAD → ratio met but z-score below threshold."""
    assert (
        detect_order_volume_spike(
            snap(order_count=39),
            baseline(order_count=mb("18.0000", mad="15.0000")),
        )
        is None
    )


def test_insufficient_sample_does_not_fire() -> None:
    assert (
        detect_order_volume_spike(
            snap(order_count=MIN_ORDER_COUNT - 1),
            baseline(order_count=mb("18.0000", mad="1.0000")),
        )
        is None
    )


def test_none_baseline_median_does_not_fire() -> None:
    assert (
        detect_order_volume_spike(
            snap(order_count=39),
            baseline(order_count=mb(None)),
        )
        is None
    )


def test_no_source_event_ids_does_not_fire() -> None:
    assert (
        detect_order_volume_spike(
            snap(order_count=39, source_event_ids=()),
            baseline(order_count=mb("18.0000", mad="1.0000")),
        )
        is None
    )


def test_zero_baseline_fires_when_current_positive() -> None:
    result = detect_order_volume_spike(
        snap(order_count=20),
        baseline(order_count=mb("0.0000", mad="0.0000")),
    )
    assert result is not None
    assert result.baseline_value == Decimal("0")
    assert result.deviation_ratio == Decimal("0")


def test_severity_bounded() -> None:
    result = detect_order_volume_spike(
        snap(order_count=100),
        baseline(order_count=mb("10.0000", mad="1.0000")),
    )
    assert result is not None
    assert 0.0 <= result.severity <= 1.0


def test_deterministic_signal_id() -> None:
    s = snap(order_count=39)
    b = baseline(order_count=mb("18.0000", mad="1.0000"))
    r1 = detect_order_volume_spike(s, b)
    r2 = detect_order_volume_spike(s, b)
    assert r1 is not None and r2 is not None
    assert r1.signal_id == r2.signal_id
    assert OUTLET in r1.signal_id
    assert "20260808T120000Z" in r1.signal_id
    assert DETECTOR_VERSION in r1.signal_id


def test_evidence_and_window_fields() -> None:
    ids = ("e1", "e2", "e3")
    result = detect_order_volume_spike(
        snap(order_count=39, source_event_ids=ids),
        baseline(order_count=mb("18.0000", mad="1.0000")),
    )
    assert result is not None
    assert result.window_start == W_START
    assert result.window_end == W_END
    assert set(result.evidence_event_ids) == set(ids)


def test_repeated_invocation_equivalent() -> None:
    s = snap(order_count=39)
    b = baseline(order_count=mb("18.0000", mad="1.0000"))
    results = [detect_order_volume_spike(s, b) for _ in range(3)]
    assert all(r == results[0] for r in results)


def test_outlet_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="outlet"):
        detect_order_volume_spike(
            snap(outlet_id="outlet_A", order_count=39),
            baseline(outlet_id="outlet_B", order_count=mb("18.0000", mad="1.0000")),
        )


def test_custom_threshold_overrides() -> None:
    # 22/18 ≈ 1.22× — below default 1.30× but above custom 1.20×
    s = snap(order_count=22)
    b = baseline(order_count=mb("18.0000", mad="1.0000"))
    assert detect_order_volume_spike(s, b) is None
    assert (
        detect_order_volume_spike(
            s,
            b,
            ratio_threshold=Decimal("1.20"),
            z_score_threshold=Decimal("1.0"),
        )
        is not None
    )
