"""Tests for PREP_TIME_SPIKE detector (detectors/preparation.py)."""

from decimal import Decimal

import pytest

from lossline_intelligence.detectors.preparation import (
    DETECTOR_VERSION,
    MIN_PREP_COMPLETED_COUNT,
    RATIO_THRESHOLD,
    detect_prep_time_spike,
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
    """7.0 min vs baseline 4.0 min → 1.75× > 1.40×."""
    result = detect_prep_time_spike(
        snap(
            avg_prep_minutes=Decimal("7.0000"),
            p90_prep_minutes=Decimal("9.0000"),
            prep_completed_count=10,
        ),
        baseline(avg_prep_minutes=mb("4.0000")),
    )
    assert result is not None
    assert result.signal_type is SignalType.PREP_TIME_SPIKE
    assert result.current_value == Decimal("7.0000")
    assert result.baseline_value == Decimal("4.0000")


def test_just_below_ratio_threshold_does_not_fire() -> None:
    """5.5/4.0 = 1.375× < 1.40× → no fire."""
    assert (
        detect_prep_time_spike(
            snap(
                avg_prep_minutes=Decimal("5.5000"),
                prep_completed_count=10,
            ),
            baseline(avg_prep_minutes=mb("4.0000")),
        )
        is None
    )


def test_insufficient_prep_count_does_not_fire() -> None:
    assert (
        detect_prep_time_spike(
            snap(
                avg_prep_minutes=Decimal("7.0000"),
                prep_completed_count=MIN_PREP_COMPLETED_COUNT - 1,
            ),
            baseline(avg_prep_minutes=mb("4.0000")),
        )
        is None
    )


def test_none_baseline_median_does_not_fire() -> None:
    assert (
        detect_prep_time_spike(
            snap(
                avg_prep_minutes=Decimal("7.0000"),
                prep_completed_count=10,
            ),
            baseline(avg_prep_minutes=mb(None)),
        )
        is None
    )


def test_zero_baseline_fires_when_current_positive() -> None:
    result = detect_prep_time_spike(
        snap(
            avg_prep_minutes=Decimal("5.0000"),
            prep_completed_count=10,
        ),
        baseline(avg_prep_minutes=mb("0.0000")),
    )
    assert result is not None
    assert result.deviation_ratio == Decimal("0")


def test_zero_baseline_zero_current_does_not_fire() -> None:
    assert (
        detect_prep_time_spike(
            snap(prep_completed_count=10),
            baseline(avg_prep_minutes=mb("0.0000")),
        )
        is None
    )


def test_severity_bounded() -> None:
    result = detect_prep_time_spike(
        snap(
            avg_prep_minutes=Decimal("20.0000"),
            prep_completed_count=10,
        ),
        baseline(avg_prep_minutes=mb("2.0000")),
    )
    assert result is not None
    assert 0.0 <= result.severity <= 1.0


def test_deterministic_signal_id() -> None:
    s = snap(
        avg_prep_minutes=Decimal("7.0000"),
        prep_completed_count=10,
    )
    b = baseline(avg_prep_minutes=mb("4.0000"))
    r1 = detect_prep_time_spike(s, b)
    r2 = detect_prep_time_spike(s, b)
    assert r1 is not None and r2 is not None
    assert r1.signal_id == r2.signal_id
    assert DETECTOR_VERSION in r1.signal_id


def test_evidence_and_window_fields() -> None:
    ids = ("prep_1", "prep_2")
    result = detect_prep_time_spike(
        snap(
            avg_prep_minutes=Decimal("7.0000"),
            prep_completed_count=10,
            source_event_ids=ids,
        ),
        baseline(avg_prep_minutes=mb("4.0000")),
    )
    assert result is not None
    assert result.window_start == W_START
    assert result.window_end == W_END
    assert set(result.evidence_event_ids) == set(ids)
    assert result.unit == "minutes"


def test_repeated_invocation_equivalent() -> None:
    s = snap(
        avg_prep_minutes=Decimal("7.0000"),
        prep_completed_count=10,
    )
    b = baseline(avg_prep_minutes=mb("4.0000"))
    assert detect_prep_time_spike(s, b) == detect_prep_time_spike(s, b)


def test_outlet_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="outlet"):
        detect_prep_time_spike(
            snap(
                outlet_id="A",
                avg_prep_minutes=Decimal("7.0000"),
                prep_completed_count=10,
            ),
            baseline(
                outlet_id="B",
                avg_prep_minutes=mb("4.0000"),
            ),
        )
