"""Minimal demonstration of the Cancellation Agent.

Run from the intelligence package root:
    python demo_cancellation.py

No CLI framework.  No API.  No logging infrastructure.
"""

from datetime import datetime, timezone

from lossline_intelligence.cancellation import (
    CancellationMetrics,
    detect_cancellation_spike,
)

# -------------------------------------------------------------------
# Demo scenario: current=18%, baseline=7%  =>  CRITICAL spike
# -------------------------------------------------------------------
DEMO_METRICS = CancellationMetrics(
    restaurant_id="store_demo",
    current_rate=0.18,
    baseline_rate=0.07,
    window_start=datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
    window_end=datetime(2026, 8, 8, 12, 30, tzinfo=timezone.utc),
    evidence_ids=("evt_demo_001", "evt_demo_002"),
)


def main() -> None:
    print("=" * 58)
    print("  LOSSLine -- Cancellation Agent Demo")
    print("=" * 58)
    print(f"  Restaurant  : {DEMO_METRICS.restaurant_id}")
    print(f"  Current rate: {DEMO_METRICS.current_rate:.1%}")
    print(f"  Baseline    : {DEMO_METRICS.baseline_rate:.1%}")
    print(
        f"  Window      : {DEMO_METRICS.window_start.isoformat()} -> "
        f"{DEMO_METRICS.window_end.isoformat()}"
    )
    print("-" * 58)

    result = detect_cancellation_spike(DEMO_METRICS)

    if result is None:
        print("  [OK] No signal -- cancellation rate is within normal range.")
    else:
        sig = result.signal
        print("  [!] SIGNAL RAISED")
        print(f"  Signal Type      : {sig.signal_type}")
        print(f"  Severity (label) : {result.severity}")
        print(f"  Severity (score) : {sig.severity:.2f}  "
              "[confidence, capped at 0.95]")
        print(f"  Current Value    : {float(sig.current_value):.1%}")
        print(f"  Baseline Value   : {float(sig.baseline_value):.1%}")
        print(f"  Deviation        : {result.deviation_percent:.2f}%")
        print(f"  Detector Version : {sig.detector_version}")
        print(f"  Signal ID        : {sig.signal_id}")
        print("-" * 58)
        print(f"  Message: {result.message}")

    print("=" * 58)


if __name__ == "__main__":
    main()
