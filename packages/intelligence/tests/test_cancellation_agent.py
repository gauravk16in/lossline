"""Tests for the Cancellation Agent (detect_cancellation_spike).

Tests cover observable behaviour only — not internal implementation details.

Threshold reference (deviation from baseline):
  < 25 %          → None
  25 – 49.99 %    → LOW
  50 – 99.99 %    → MEDIUM
  100 – 149.99 %  → HIGH
  150 % +         → CRITICAL
"""

import pytest

from lossline_intelligence.agents.cancellation import (
    CancellationMetrics,
    detect_cancellation_spike,
)
from lossline_intelligence.models.signal import Severity, SignalType
from .fixtures.cancellation_fixtures import (
    CRITICAL_METRICS,
    HIGH_METRICS,
    NORMAL_METRICS,
)


# ---------------------------------------------------------------------------
# Test 1 — Normal: no signal should be raised
# current=0.08, baseline=0.07 → deviation ≈ 14.3 % → below 25 % → None
# ---------------------------------------------------------------------------

def test_normal_rate_returns_none() -> None:
    result = detect_cancellation_spike(NORMAL_METRICS)
    assert result is None


# ---------------------------------------------------------------------------
# Test 2 — HIGH: 100–149.99 % deviation bracket
# current=0.14, baseline=0.07 → deviation = 100.0 % → HIGH
# ---------------------------------------------------------------------------

def test_high_rate_raises_correct_signal() -> None:
    result = detect_cancellation_spike(HIGH_METRICS)

    assert result is not None

    # Signal type
    assert result.signal.signal_type is SignalType.CANCELLATION_SPIKE

    # Categorical severity label — HIGH sits in the 100–149.99 % band
    assert result.severity is Severity.HIGH

    # Deviation must match the formula: ((current - baseline) / baseline) * 100
    expected_deviation = ((HIGH_METRICS.current_rate - HIGH_METRICS.baseline_rate)
                          / HIGH_METRICS.baseline_rate) * 100.0
    assert abs(result.deviation_percent - expected_deviation) < 0.01

    # Confidence is a heuristic; must never exceed 0.95
    assert result.signal.severity <= 0.95


# ---------------------------------------------------------------------------
# Test 3 — CRITICAL: 150 %+ deviation bracket
# current=0.18, baseline=0.07 → deviation ≈ 157.14 % → CRITICAL
# (Note: 0.25/0.07 fixture is also CRITICAL at ≈ 257 %, used for extra cover)
# ---------------------------------------------------------------------------

def test_critical_rate_raises_correct_signal() -> None:
    result = detect_cancellation_spike(CRITICAL_METRICS)

    assert result is not None
    assert result.signal.signal_type is SignalType.CANCELLATION_SPIKE
    assert result.severity is Severity.CRITICAL
    assert result.signal.severity <= 0.95


# ---------------------------------------------------------------------------
# Guard: zero baseline must raise, not silently divide by zero
# ---------------------------------------------------------------------------

def test_zero_baseline_raises_value_error() -> None:
    from datetime import datetime, timedelta, timezone

    metrics = CancellationMetrics(
        outlet_id="store_guard",
        current_rate=0.10,
        baseline_rate=0.0,
        window_start=datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 8, 8, 12, 30, tzinfo=timezone.utc),
        evidence_ids=("evt_guard_001",),
    )

    with pytest.raises(ValueError, match="baseline_rate"):
        detect_cancellation_spike(metrics)
