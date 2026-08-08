from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.agents.cancellation import (
    CancellationMetrics,
    Severity,
    detect_cancellation_spike,
)
from lossline_intelligence.models.signal import SignalType


WINDOW_START = datetime(2026, 8, 8, 7, 30, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc)


def metrics(
    *,
    current_rate: float = 0.08,
    baseline_rate: float = 0.04,
) -> CancellationMetrics:
    return CancellationMetrics(
        outlet_id="outlet_17",
        current_rate=current_rate,
        baseline_rate=baseline_rate,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        evidence_ids=("evt_001", "evt_002"),
    )


def test_returns_none_below_low_threshold() -> None:
    assert detect_cancellation_spike(metrics(current_rate=0.0499)) is None


@pytest.mark.parametrize(
    ("current_rate", "expected_severity", "expected_score"),
    [
        (0.05, Severity.LOW, 0.25),
        (0.06, Severity.MEDIUM, 0.50),
        (0.08, Severity.HIGH, 0.75),
        (0.10, Severity.CRITICAL, 0.95),
    ],
)
def test_classifies_exact_threshold_boundaries(
    current_rate: float,
    expected_severity: Severity,
    expected_score: float,
) -> None:
    result = detect_cancellation_spike(metrics(current_rate=current_rate))

    assert result is not None
    assert result.severity is expected_severity
    assert result.signal.severity == expected_score


def test_emits_signal_matching_current_contract() -> None:
    result = detect_cancellation_spike(metrics())

    assert result is not None
    assert result.signal.outlet_id == "outlet_17"
    assert result.signal.signal_type is SignalType.CANCELLATION_SPIKE
    assert result.signal.current_value == Decimal("0.08")
    assert result.signal.baseline_value == Decimal("0.04")
    assert result.signal.deviation_ratio == Decimal("1")
    assert result.signal.unit == "ratio"
    assert result.signal.evidence_event_ids == ("evt_001", "evt_002")
    assert result.signal.metadata == {
        "threshold_ratio": "0.25",
        "severity_band": "HIGH",
    }
    assert result.deviation_percent == 100.0
    assert "severity=HIGH" in result.message


def test_replay_produces_same_signal() -> None:
    first = detect_cancellation_spike(metrics())
    second = detect_cancellation_spike(metrics())

    assert first == second
    assert first is not None
    assert first.signal.signal_id == "sig_cancellation_outlet_17_20260808T073000Z"


def test_signal_id_normalizes_offset_window_to_utc() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    offset_metrics = CancellationMetrics(
        outlet_id="outlet_17",
        current_rate=0.08,
        baseline_rate=0.04,
        window_start=datetime(2026, 8, 8, 13, 0, tzinfo=offset),
        window_end=datetime(2026, 8, 8, 13, 30, tzinfo=offset),
        evidence_ids=("evt_001",),
    )

    result = detect_cancellation_spike(offset_metrics)

    assert result is not None
    assert result.signal.signal_id == "sig_cancellation_outlet_17_20260808T073000Z"
    assert result.signal.window_start == WINDOW_START


@pytest.mark.parametrize(
    "invalid_metrics",
    [
        metrics(current_rate=-0.01),
        metrics(current_rate=1.01),
        metrics(current_rate=float("nan")),
        metrics(baseline_rate=0),
        metrics(baseline_rate=-0.01),
        metrics(baseline_rate=float("inf")),
        CancellationMetrics("", 0.08, 0.04, WINDOW_START, WINDOW_END, ("evt",)),
        CancellationMetrics(
            "outlet_17",
            0.08,
            0.04,
            WINDOW_START.replace(tzinfo=None),
            WINDOW_END,
            ("evt",),
        ),
        CancellationMetrics(
            "outlet_17", 0.08, 0.04, WINDOW_END, WINDOW_START, ("evt",)
        ),
        CancellationMetrics("outlet_17", 0.08, 0.04, WINDOW_START, WINDOW_END, ()),
        CancellationMetrics(
            "outlet_17",
            0.08,
            0.04,
            WINDOW_START,
            WINDOW_END,
            ("evt", "evt"),
        ),
    ],
)
def test_rejects_invalid_metrics(invalid_metrics: CancellationMetrics) -> None:
    with pytest.raises(ValueError):
        detect_cancellation_spike(invalid_metrics)
