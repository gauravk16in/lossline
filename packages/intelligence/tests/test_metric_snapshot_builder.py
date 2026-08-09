"""Tests for build_metric_snapshot.

Coverage:
  - empty event list → zeroed snapshot
  - window boundary semantics (half-open [start, end))
  - order.created counting + delivery channel detection
  - order.cancelled → cancellation_rate
  - cancellation_rate = 0 when order_count == 0
  - preparation.completed → avg_prep_minutes, p90_prep_minutes
  - delivery.handoff_completed → avg_handoff_wait_minutes
  - review.received → review_count, negative_review_count, delay_review_count
  - events from other outlets are ignored
  - deterministic replay
  - invalid inputs raise ValueError
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.aggregation.metric_snapshot_builder import (
    NormalizedEvent,
    build_metric_snapshot,
)
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot


# ---------------------------------------------------------------------------
# Shared window
# ---------------------------------------------------------------------------
_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_W_END = _W_START + timedelta(minutes=30)
_OUTLET = "outlet_test"


def _evt(
    event_id: str,
    event_type: str,
    offset_minutes: float = 0,
    **kwargs,
) -> NormalizedEvent:
    """Factory: create a NormalizedEvent in the default window."""
    return NormalizedEvent(
        event_id=event_id,
        outlet_id=_OUTLET,
        event_type=event_type,
        occurred_at=_W_START + timedelta(minutes=offset_minutes),
        **kwargs,
    )


def _build(**kwargs) -> MetricSnapshot:
    """Call build_metric_snapshot with defaults, accepting overrides."""
    return build_metric_snapshot(
        kwargs.pop("events", []),
        outlet_id=kwargs.pop("outlet_id", _OUTLET),
        window_start=kwargs.pop("window_start", _W_START),
        window_end=kwargs.pop("window_end", _W_END),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Empty / sparse
# ---------------------------------------------------------------------------

def test_empty_events_produces_zeroed_snapshot() -> None:
    snap = _build(events=[])

    assert snap.order_count == 0
    assert snap.delivery_order_count == 0
    assert snap.cancelled_order_count == 0
    assert snap.cancellation_rate == Decimal("0")
    assert snap.avg_prep_minutes == Decimal("0")
    assert snap.p90_prep_minutes == Decimal("0")
    assert snap.prep_completed_count == 0
    assert snap.avg_handoff_wait_minutes == Decimal("0")
    assert snap.handoff_completed_count == 0
    assert snap.review_count == 0
    assert snap.negative_review_count == 0
    assert snap.delay_review_count == 0
    assert snap.delay_review_event_ids == ()
    assert snap.source_event_ids == ()


def test_cancellation_rate_zero_when_no_orders() -> None:
    """Zero order.created events → cancellation_rate=0 (no div/zero)."""
    snap = _build(events=[])  # no events at all
    assert snap.cancellation_rate == Decimal("0")
    assert snap.order_count == 0
    assert snap.cancelled_order_count == 0


# ---------------------------------------------------------------------------
# Window boundary
# ---------------------------------------------------------------------------

def test_event_at_window_start_is_included() -> None:
    events = [_evt("e1", "order.created", offset_minutes=0, channel="pos")]
    snap = _build(events=events)
    assert snap.order_count == 1


def test_event_at_window_end_is_excluded() -> None:
    """occurred_at == window_end is outside the half-open [start, end)."""
    events = [
        NormalizedEvent(
            event_id="e_late",
            outlet_id=_OUTLET,
            event_type="order.created",
            occurred_at=_W_END,          # exactly at end → excluded
            channel="pos",
        )
    ]
    snap = _build(events=events)
    assert snap.order_count == 0


def test_event_before_window_is_excluded() -> None:
    early = NormalizedEvent(
        event_id="e_early",
        outlet_id=_OUTLET,
        event_type="order.created",
        occurred_at=_W_START - timedelta(seconds=1),
        channel="pos",
    )
    snap = _build(events=[early])
    assert snap.order_count == 0


# ---------------------------------------------------------------------------
# Order counts
# ---------------------------------------------------------------------------

def test_order_count_and_delivery_channel() -> None:
    events = [
        _evt("e1", "order.created", 1, channel="pos"),       # not delivery
        _evt("e2", "order.created", 2, channel="delivery"),  # delivery
        _evt("e3", "order.created", 3, channel="Zomato"),    # delivery (case-insensitive)
    ]
    snap = _build(events=events)
    assert snap.order_count == 3
    assert snap.delivery_order_count == 2


def test_cancellation_rate_computed_correctly() -> None:
    events = [
        _evt("e1", "order.created", 1, channel="pos", entity_id="order-1"),
        _evt("e2", "order.created", 2, channel="pos", entity_id="order-2"),
        _evt("e3", "order.created", 3, channel="pos"),
        _evt("e4", "order.created", 4, channel="pos"),
        _evt("e5", "order.cancelled", 5, channel="pos", entity_id="order-1"),
        _evt("e6", "order.cancelled", 6, channel="pos", entity_id="order-2"),
    ]
    snap = _build(events=events)
    assert snap.order_count == 4
    assert snap.cancelled_order_count == 2
    # 2/4 = 0.5
    assert snap.cancellation_rate == Decimal("0.5000")


def test_unmatched_pre_window_cancellation_is_excluded() -> None:
    events = [
        _evt("created", "order.created", 1, channel="pos", entity_id="new-order"),
        _evt("cancelled", "order.cancelled", 2, channel="pos", entity_id="old-order"),
    ]
    snap = _build(events=events)
    assert snap.cancelled_order_count == 0
    assert snap.cancellation_rate == Decimal("0.0000")


# ---------------------------------------------------------------------------
# Prep time
# ---------------------------------------------------------------------------

def test_avg_and_p90_prep_minutes() -> None:
    # 60s, 120s, 180s → mean=120s=2 min; p90=180s=3 min (3rd of 3 items)
    events = [
        _evt("p1", "preparation.completed", 5, duration_seconds=60.0),
        _evt("p2", "preparation.completed", 6, duration_seconds=120.0),
        _evt("p3", "preparation.completed", 7, duration_seconds=180.0),
    ]
    snap = _build(events=events)
    assert snap.avg_prep_minutes == Decimal("2.0000")
    assert snap.prep_completed_count == 3
    # p90 index = max(0, int(3 * 0.9) - 1) = 1 → sorted[1] = 120s = 2.0 min
    assert snap.p90_prep_minutes == Decimal("2.0000")


def test_no_prep_events_yields_zero_prep_metrics() -> None:
    events = [_evt("e1", "order.created", 1, channel="pos")]
    snap = _build(events=events)
    assert snap.avg_prep_minutes == Decimal("0")
    assert snap.p90_prep_minutes == Decimal("0")


# ---------------------------------------------------------------------------
# Handoff wait
# ---------------------------------------------------------------------------

def test_avg_handoff_wait_minutes() -> None:
    # 300s = 5 min, 600s = 10 min → mean = 7.5 min
    events = [
        _evt("h1", "delivery.handoff_completed", 5, wait_seconds=300.0),
        _evt("h2", "delivery.handoff_completed", 6, wait_seconds=600.0),
    ]
    snap = _build(events=events)
    assert snap.avg_handoff_wait_minutes == Decimal("7.5000")
    assert snap.handoff_completed_count == 2


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

def test_review_counts() -> None:
    events = [
        _evt("r1", "review.received", 1, rating=5, text="Great food!"),   # positive
        _evt("r2", "review.received", 2, rating=2, text="Very slow delivery"),  # neg+delay
        _evt("r3", "review.received", 3, rating=1, text="Bad quality"),   # neg, no delay kw
        _evt("r4", "review.received", 4, rating=3, text="Late order"),    # not negative (>2)
    ]
    snap = _build(events=events)
    assert snap.review_count == 4
    assert snap.negative_review_count == 2   # ratings 2 and 1
    assert snap.delay_review_count == 1      # only r2 has delay keyword "slow"
    assert snap.delay_review_event_ids == ("r2",)


# ---------------------------------------------------------------------------
# Multi-outlet isolation
# ---------------------------------------------------------------------------

def test_events_for_other_outlet_are_ignored() -> None:
    events = [
        _evt("e1", "order.created", 1, channel="pos"),  # correct outlet
        NormalizedEvent(                                  # different outlet
            event_id="e2",
            outlet_id="other_outlet",
            event_type="order.created",
            occurred_at=_W_START + timedelta(minutes=2),
            channel="pos",
        ),
    ]
    snap = _build(events=events)
    assert snap.order_count == 1


# ---------------------------------------------------------------------------
# Source event IDs
# ---------------------------------------------------------------------------

def test_source_event_ids_contains_all_contributing_events() -> None:
    events = [
        _evt("e1", "order.created", 1, channel="pos"),
        _evt("e2", "preparation.completed", 5, duration_seconds=90.0),
        _evt("e3", "review.received", 10, rating=4, text="Good"),
    ]
    snap = _build(events=events)
    assert set(snap.source_event_ids) == {"e1", "e2", "e3"}


# ---------------------------------------------------------------------------
# Mixed full scenario
# ---------------------------------------------------------------------------

def test_full_scenario_snapshot() -> None:
    """One order, one cancellation, one prep, one handoff, two reviews."""
    events = [
        _evt("o1", "order.created", 1, channel="delivery", entity_id="order-1"),
        _evt("o2", "order.created", 2, channel="pos"),
        _evt("c1", "order.cancelled", 3, channel="delivery", entity_id="order-1"),
        _evt("p1", "preparation.completed", 5, duration_seconds=240.0),  # 4 min
        _evt("h1", "delivery.handoff_completed", 8, wait_seconds=120.0),  # 2 min
        _evt("rv1", "review.received", 10, rating=1, text="so delayed and cold"),
        _evt("rv2", "review.received", 11, rating=4, text="Lovely food"),
    ]
    snap = _build(events=events)

    assert snap.order_count == 2
    assert snap.delivery_order_count == 1
    assert snap.cancelled_order_count == 1
    assert snap.cancellation_rate == Decimal("0.5000")
    assert snap.avg_prep_minutes == Decimal("4.0000")
    assert snap.prep_completed_count == 1
    assert snap.avg_handoff_wait_minutes == Decimal("2.0000")
    assert snap.handoff_completed_count == 1
    assert snap.review_count == 2
    assert snap.negative_review_count == 1
    assert snap.delay_review_count == 1
    assert snap.delay_review_event_ids == ("rv1",)
    assert len(snap.source_event_ids) == 7


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic_replay() -> None:
    events = [
        _evt("e1", "order.created", 1, channel="delivery"),
        _evt("e2", "preparation.completed", 5, duration_seconds=300.0),
    ]
    s1 = _build(events=events)
    s2 = _build(events=events)
    assert s1 == s2


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("outlet_id", ["", "   "])
def test_raises_on_empty_outlet_id(outlet_id: str) -> None:
    with pytest.raises(ValueError, match="outlet_id"):
        _build(outlet_id=outlet_id)


def test_raises_on_reversed_window() -> None:
    with pytest.raises(ValueError, match="window_end"):
        _build(window_start=_W_END, window_end=_W_START)


def test_raises_on_naive_window_start() -> None:
    with pytest.raises(ValueError, match="window_start"):
        _build(window_start=_W_START.replace(tzinfo=None))


def test_raises_on_naive_window_end() -> None:
    with pytest.raises(ValueError, match="window_end"):
        _build(window_end=_W_END.replace(tzinfo=None))


# ---------------------------------------------------------------------------
# UTC normalization of window timestamps
# ---------------------------------------------------------------------------

def test_non_utc_window_is_normalized() -> None:
    """Window timestamps with non-UTC offsets are normalized to UTC by MetricSnapshot."""
    offset = timezone(timedelta(hours=5, minutes=30))
    w_start_ist = datetime(2026, 8, 8, 17, 30, tzinfo=offset)   # 12:00 UTC
    w_end_ist = datetime(2026, 8, 8, 18, 0, tzinfo=offset)       # 12:30 UTC

    # An event at the same wall-clock time expressed in UTC
    events = [
        NormalizedEvent(
            event_id="e1",
            outlet_id=_OUTLET,
            event_type="order.created",
            occurred_at=datetime(2026, 8, 8, 12, 5, tzinfo=timezone.utc),
            channel="pos",
        )
    ]
    snap = build_metric_snapshot(events, outlet_id=_OUTLET, window_start=w_start_ist, window_end=w_end_ist)
    assert snap.window_start == datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    assert snap.order_count == 1
