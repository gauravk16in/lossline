"""Deterministic fixtures for the Cancellation Agent.

These fixtures represent fixed, repeatable metric snapshots used for
testing detect_cancellation_spike.  Not connected to any database, Redis,
simulator, or external service.

Deviation calculations (all use baseline=0.07):
------------------------------------------------
NORMAL   : current=0.08 → (0.08-0.07)/0.07 * 100 ≈  14.3 %  → None
MODERATE : current=0.11 → (0.11-0.07)/0.07 * 100 ≈  57.1 %  → MEDIUM
HIGH     : current=0.14 → (0.14-0.07)/0.07 * 100 = 100.0 %   → HIGH
CRITICAL : current=0.18 → (0.18-0.07)/0.07 * 100 ≈ 157.1 %  → CRITICAL
           current=0.25 → (0.25-0.07)/0.07 * 100 ≈ 257.1 %  → CRITICAL

Threshold reference:
  < 25 %          → None
  25 – 49.99 %    → LOW
  50 – 99.99 %    → MEDIUM
  100 – 149.99 %  → HIGH
  150 % +         → CRITICAL
"""

from datetime import datetime, timedelta, timezone

from lossline_intelligence.agents.cancellation import CancellationMetrics

# Fixed reference window shared by all fixtures.
_WINDOW_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_WINDOW_END = _WINDOW_START + timedelta(minutes=30)

NORMAL_METRICS = CancellationMetrics(
    outlet_id="store_test",
    current_rate=0.08,   # ≈ 14.3 % deviation → None
    baseline_rate=0.07,
    window_start=_WINDOW_START,
    window_end=_WINDOW_END,
    evidence_ids=("evt_normal_001",),
)

MODERATE_METRICS = CancellationMetrics(
    outlet_id="store_test",
    current_rate=0.11,   # ≈ 57.1 % deviation → MEDIUM
    baseline_rate=0.07,
    window_start=_WINDOW_START,
    window_end=_WINDOW_END,
    evidence_ids=("evt_moderate_001",),
)

HIGH_METRICS = CancellationMetrics(
    outlet_id="store_test",
    current_rate=0.14,   # exactly 100.0 % deviation → HIGH
    baseline_rate=0.07,
    window_start=_WINDOW_START,
    window_end=_WINDOW_END,
    evidence_ids=("evt_high_001", "evt_high_002"),
)

CRITICAL_METRICS = CancellationMetrics(
    outlet_id="store_test",
    current_rate=0.18,   # ≈ 157.1 % deviation → CRITICAL
    baseline_rate=0.07,
    window_start=_WINDOW_START,
    window_end=_WINDOW_END,
    evidence_ids=("evt_critical_001", "evt_critical_002"),
)
