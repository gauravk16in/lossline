"""Tests for DELAY_REVIEW_SPIKE detector (detectors/reviews.py)."""

import pytest

from lossline_intelligence.detectors.reviews import (
    DETECTOR_VERSION,
    MIN_QUALIFYING_REVIEWS,
    detect_delay_review_spike,
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
    result = detect_delay_review_spike(
        snap(
            review_count=5,
            negative_review_count=3,
            delay_review_count=2,
            delay_review_event_ids=("rev_1", "rev_2"),
        ),
        baseline(delay_review_rate=mb("0.1000")),
    )
    assert result is not None
    assert result.signal_type is SignalType.DELAY_REVIEW_SPIKE
    assert result.current_value == 2


def test_one_review_below_threshold_does_not_fire() -> None:
    assert (
        detect_delay_review_spike(
            snap(
                review_count=1,
                negative_review_count=1,
                delay_review_count=1,
                delay_review_event_ids=("rev_1",),
            ),
            baseline(),
        )
        is None
    )


def test_count_met_but_no_evidence_ids_does_not_fire() -> None:
    assert (
        detect_delay_review_spike(
            snap(
                review_count=3,
                delay_review_count=3,
                delay_review_event_ids=(),
            ),
            baseline(),
        )
        is None
    )


def test_no_reviews_does_not_fire() -> None:
    assert detect_delay_review_spike(snap(), baseline()) is None


def test_severity_bounded() -> None:
    ids = tuple(f"rev_{i}" for i in range(10))
    result = detect_delay_review_spike(
        snap(
            review_count=10,
            delay_review_count=10,
            delay_review_event_ids=ids,
        ),
        baseline(),
    )
    assert result is not None
    assert 0.0 <= result.severity <= 1.0


def test_severity_scales_with_count() -> None:
    low = detect_delay_review_spike(
        snap(
            review_count=2,
            delay_review_count=2,
            delay_review_event_ids=("a", "b"),
        ),
        baseline(),
    )
    high = detect_delay_review_spike(
        snap(
            review_count=8,
            delay_review_count=8,
            delay_review_event_ids=tuple(f"r{i}" for i in range(8)),
        ),
        baseline(),
    )
    assert low is not None and high is not None
    assert low.severity <= high.severity


def test_deterministic_signal_id() -> None:
    s = snap(
        review_count=2,
        delay_review_count=2,
        delay_review_event_ids=("rev_1", "rev_2"),
    )
    b = baseline()
    r1 = detect_delay_review_spike(s, b)
    r2 = detect_delay_review_spike(s, b)
    assert r1 is not None and r2 is not None
    assert r1.signal_id == r2.signal_id
    assert DETECTOR_VERSION in r1.signal_id


def test_evidence_ids_are_delay_reviews_only() -> None:
    ids = ("bad_1", "bad_2", "bad_3")
    result = detect_delay_review_spike(
        snap(
            review_count=4,
            delay_review_count=3,
            delay_review_event_ids=ids,
            source_event_ids=("bad_1", "bad_2", "bad_3", "good_1"),
        ),
        baseline(),
    )
    assert result is not None
    assert result.evidence_event_ids == ids
    assert result.window_start == W_START
    assert result.window_end == W_END
    assert result.unit == "qualifying_reviews"


def test_repeated_invocation_equivalent() -> None:
    s = snap(
        review_count=2,
        delay_review_count=2,
        delay_review_event_ids=("rev_1", "rev_2"),
    )
    b = baseline()
    assert detect_delay_review_spike(s, b) == detect_delay_review_spike(s, b)


def test_outlet_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="outlet"):
        detect_delay_review_spike(
            snap(
                outlet_id="A",
                review_count=2,
                delay_review_count=2,
                delay_review_event_ids=("r1", "r2"),
            ),
            baseline(outlet_id="B"),
        )


def test_custom_min_qualifying_reviews() -> None:
    s = snap(
        review_count=3,
        delay_review_count=3,
        delay_review_event_ids=("a", "b", "c"),
    )
    b = baseline()
    assert detect_delay_review_spike(s, b) is not None
    assert (
        detect_delay_review_spike(s, b, min_qualifying_reviews=4) is None
    )
