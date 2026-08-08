"""Tests for HANDOFF_DELAY_SPIKE detector (detectors/handoff.py)."""

from decimal import Decimal

import pytest

from lossline_intelligence.detectors.handoff import (
    DETECTOR_VERSION,
    MIN_HANDOFF_COMPLETED_COUNT,
    detect_handoff_delay_spike,
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
    """5.83 min vs baseline 3.33 min → ~1.75× > 1.40×."""
    result = detect_handoff_delay_spike(
        snap(
            avg_handoff_wait_minutes=Decimal("5.8333"),
            handoff_completed_count=10,
        ),
        baseline(avg_handoff_wait_minutes=mb("3.3333")),
    )
    assert result is not None
    assert result.signal_type is SignalType.HANDOFF_DELAY_SPIKE


def test_just_below_ratio_threshold_does_not_fire() -> None:
    """4.6/3.33 ≈ 1.38× < 1.40× → no fire."""
    assert (
        detect_handoff_delay_spike(
            snap(
                avg_handoff_wait_minutes=Decimal("4.6000"),
                handoff_completed_count=10,
            ),
            baseline(avg_handoff_wait_minutes=mb("3.3333")),
        )
        is None
    )


def test_insufficient_handoff_count_does_not_fire() -> None:
    assert (
        detect_handoff_delay_spike(
            snap(
                avg_handoff_wait_minutes=Decimal("8.0000"),
                handoff_completed_count=MIN_HANDOFF_COMPLETED_COUNT - 1,
            ),
            baseline(avg_handoff_wait_minutes=mb("3.3333")),
        )
        is None
    )


def test_none_baseline_median_does_not_fire() -> None:
    assert (
        detect_handoff_delay_spike(
            snap(
                avg_handoff_wait_minutes=Decimal("8.0000"),
                handoff_completed_count=10,
            ),
            baseline(avg_handoff_wait_minutes=mb(None)),
        )
        is None
    )


def test_zero_baseline_fires_when_current_positive() -> None:
    result = detect_handoff_delay_spike(
        snap(
            avg_handoff_wait_minutes=Decimal("4.0000"),
            handoff_completed_count=10,
        ),
        baseline(avg_handoff_wait_minutes=mb("0.0000")),
    )
    assert result is not None
    assert result.deviation_ratio == Decimal("0")


def test_severity_bounded() -> None:
    result = detect_handoff_delay_spike(
        snap(
            avg_handoff_wait_minutes=Decimal("20.0000"),
            handoff_completed_count=10,
        ),
        baseline(avg_handoff_wait_minutes=mb("2.0000")),
    )
    assert result is not None
    assert 0.0 <= result.severity <= 1.0


def test_deterministic_signal_id() -> None:
    s = snap(
        avg_handoff_wait_minutes=Decimal("8.0000"),
        handoff_completed_count=10,
    )
    b = baseline(avg_handoff_wait_minutes=mb("3.3333"))
    r1 = detect_handoff_delay_spike(s, b)
    r2 = detect_handoff_delay_spike(s, b)
    assert r1 is not None and r2 is not None
    assert r1.signal_id == r2.signal_id
    assert DETECTOR_VERSION in r1.signal_id


def test_evidence_and_window_fields() -> None:
    ids = ("h1", "h2")
    result = detect_handoff_delay_spike(
        snap(
            avg_handoff_wait_minutes=Decimal("8.0000"),
            handoff_completed_count=10,
            source_event_ids=ids,
        ),
        baseline(avg_handoff_wait_minutes=mb("3.3333")),
    )
    assert result is not None
    assert result.window_start == W_START
    assert result.window_end == W_END
    assert set(result.evidence_event_ids) == set(ids)


def test_repeated_invocation_equivalent() -> None:
    s = snap(
        avg_handoff_wait_minutes=Decimal("8.0000"),
        handoff_completed_count=10,
    )
    b = baseline(avg_handoff_wait_minutes=mb("3.3333"))
    assert detect_handoff_delay_spike(s, b) == detect_handoff_delay_spike(s, b)


def test_outlet_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="outlet"):
        detect_handoff_delay_spike(
            snap(
                outlet_id="A",
                avg_handoff_wait_minutes=Decimal("8.0000"),
                handoff_completed_count=10,
            ),
            baseline(
                outlet_id="B",
                avg_handoff_wait_minutes=mb("3.3333"),
            ),
        )
