"""Pure aggregation function: NormalizedEvent sequence → MetricSnapshot.

Responsibility
--------------
Turn a flat sequence of validated, normalized events into a single
MetricSnapshot for one outlet and one analysis window.

What this module does NOT do
-----------------------------
- No anomaly detection, baselines, correlation, confidence, recommendations.
- No I/O, no database, no Redis, no LLM calls.
- No side effects of any kind.

NormalizedEvent field notes (all derived from FINAL_IMPLEMENTATION_PLAN
§"Canonical Event Contracts"):
  order.created             → channel, amount
  order.completed           → channel, amount
  order.cancelled           → channel, amount, reason_code
  preparation.completed     → order_id, duration_seconds
  delivery.handoff_completed→ order_id, wait_seconds
  review.received           → rating, text
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot

# Delay keywords reused from the delay_review detector — single source of truth.
_DELAY_KEYWORDS: frozenset[str] = frozenset(
    {
        "late",
        "delay",
        "delayed",
        "slow",
        "wait",
        "waiting",
        "long time",
        "took forever",
        "never arrived",
        "cold",
    }
)

# M1 delivery channels — orders via these channels contribute to
# delivery_order_count.
_DELIVERY_CHANNELS: frozenset[str] = frozenset(
    {"delivery", "zomato", "swiggy", "online"}
)

# Rating threshold for a "negative" review (≤ this value).
_NEGATIVE_RATING_MAX: int = 2

# Quantile for p90 prep time (index-based).
_P90_QUANTILE: float = 0.90

# Decimal precision for rate/minutes fields.
_DECIMAL_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class NormalizedEvent:
    """Minimal validated event representation consumed by the aggregation layer.

    All fields are derived directly from the canonical event envelope defined
    in FINAL_IMPLEMENTATION_PLAN §"Canonical Event Contracts".  Optional
    per-type fields are None when not applicable to the event_type.

    Attributes
    ----------
    event_id        : Globally unique event identifier.
    outlet_id       : The restaurant/outlet this event belongs to.
    event_type      : One of the M1 canonical event types.
    occurred_at     : UTC-aware event timestamp (event time, not ingestion time).
    channel         : Order channel (order.* events).
    amount          : Order value in outlet currency (order.* events).
    order_id        : Related order ID (preparation / handoff events).
    duration_seconds: Prep duration (preparation.completed only).
    wait_seconds    : Handoff wait (delivery.handoff_completed only).
    rating          : Customer rating 1–5 (review.received only).
    text            : Review body (review.received only).
    reason_code     : Cancellation reason (order.cancelled only).
    """

    event_id: str
    outlet_id: str
    event_type: str
    occurred_at: datetime
    channel: str | None = None
    amount: Decimal | None = None
    order_id: str | None = None
    entity_id: str | None = None
    duration_seconds: float | None = None
    wait_seconds: float | None = None
    rating: int | None = None
    text: str | None = field(default=None)
    reason_code: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _seconds_to_minutes(seconds: float) -> Decimal:
    """Convert seconds to minutes as a finite Decimal, rounded to 4 d.p."""
    return Decimal(str(seconds / 60.0)).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _safe_mean_minutes(values: list[float]) -> Decimal:
    """Return mean of a list in minutes; 0 if list is empty."""
    if not values:
        return Decimal("0")
    return _seconds_to_minutes(statistics.mean(values))


def _p90_minutes(values: list[float]) -> Decimal:
    """Return p90 of a list in minutes; 0 if list is empty."""
    if not values:
        return Decimal("0")
    sorted_vals = sorted(values)
    # Index-based quantile (same as numpy's nearest-rank method).
    index = max(0, int(len(sorted_vals) * _P90_QUANTILE) - 1)
    return _seconds_to_minutes(sorted_vals[index])


def _is_delivery_order(channel: str | None) -> bool:
    if channel is None:
        return False
    return channel.lower() in _DELIVERY_CHANNELS


def _contains_delay_term(text: str | None) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _DELAY_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_metric_snapshot(
    events: Sequence[NormalizedEvent],
    *,
    outlet_id: str,
    window_start: datetime,
    window_end: datetime,
) -> MetricSnapshot:
    """Aggregate a sequence of normalized events into a MetricSnapshot.

    Only events that belong to ``outlet_id`` and whose ``occurred_at`` falls
    in the half-open interval ``[window_start, window_end)`` are considered.
    Events outside the window are silently ignored (late-arrival safety).

    Parameters
    ----------
    events:
        Flat sequence of NormalizedEvent objects.  May include events for
        other outlets or outside the window — they are filtered out.
    outlet_id:
        The outlet this snapshot is for.  Non-empty string.
    window_start:
        UTC-aware start of the analysis window (inclusive).
    window_end:
        UTC-aware end of the analysis window (exclusive).

    Returns
    -------
    MetricSnapshot
        Fully validated, frozen snapshot.  Sparse/empty inputs yield zeroed
        metric fields — never a division-by-zero error.

    Raises
    ------
    ValueError
        If outlet_id is empty, or window_end <= window_start, or either
        timestamp is naive.
    """
    if not outlet_id or not outlet_id.strip():
        raise ValueError("outlet_id must be a non-empty string")
    if window_start.tzinfo is None or window_start.utcoffset() is None:
        raise ValueError("window_start must be timezone-aware")
    if window_end.tzinfo is None or window_end.utcoffset() is None:
        raise ValueError("window_end must be timezone-aware")
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")

    # --- Filter to this outlet and window [window_start, window_end) ----------
    in_window: list[NormalizedEvent] = [
        e
        for e in events
        if e.outlet_id == outlet_id
        and window_start <= e.occurred_at < window_end
    ]

    # --- Per-metric accumulators ---------------------------------------------
    order_count = 0
    delivery_order_count = 0
    cancelled_order_count = 0
    prep_durations: list[float] = []
    handoff_waits: list[float] = []
    review_count = 0
    negative_review_count = 0
    delay_review_count = 0
    delay_review_ids: list[str] = []
    source_ids: list[str] = []

    cohort_order_ids = {
        (evt.entity_id or evt.order_id)
        for evt in in_window
        if evt.event_type == "order.created" and (evt.entity_id or evt.order_id)
    }

    for evt in in_window:
        source_ids.append(evt.event_id)
        et = evt.event_type

        if et == "order.created":
            order_count += 1
            if _is_delivery_order(evt.channel):
                delivery_order_count += 1

        elif et == "order.cancelled":
            # Same-window cohort semantics: a cancellation is attributed only
            # when its order was created in this analysis window.
            cancelled_id = evt.entity_id or evt.order_id
            if cancelled_id in cohort_order_ids:
                cancelled_order_count += 1

        elif et == "preparation.completed":
            if evt.duration_seconds is not None:
                prep_durations.append(evt.duration_seconds)

        elif et == "delivery.handoff_completed":
            if evt.wait_seconds is not None:
                handoff_waits.append(evt.wait_seconds)

        elif et == "review.received":
            review_count += 1
            if evt.rating is not None and evt.rating <= _NEGATIVE_RATING_MAX:
                negative_review_count += 1
                if _contains_delay_term(evt.text):
                    delay_review_count += 1
                    delay_review_ids.append(evt.event_id)

    # --- Derived metrics ------------------------------------------------------
    if order_count > 0:
        cancellation_rate = Decimal(str(cancelled_order_count / order_count)).quantize(
            _DECIMAL_PLACES, rounding=ROUND_HALF_UP
        )
    else:
        cancellation_rate = Decimal("0")

    avg_prep_minutes = _safe_mean_minutes(prep_durations)
    p90_prep_minutes = _p90_minutes(prep_durations)
    avg_handoff_wait_minutes = _safe_mean_minutes(handoff_waits)

    # Deduplicate source IDs (guard against unexpected duplicates in input).
    unique_source_ids = tuple(dict.fromkeys(source_ids))

    # If no events at all, we still need at least one source_event_id for the
    # MetricSnapshot model; but an empty snapshot is valid (empty tuple is fine
    # because MetricSnapshot.source_event_ids has no min_length constraint).

    return MetricSnapshot.model_validate(
        {
            "outlet_id": outlet_id,
            "window_start": window_start,
            "window_end": window_end,
            "order_count": order_count,
            "delivery_order_count": delivery_order_count,
            "cancelled_order_count": cancelled_order_count,
            "cancellation_rate": cancellation_rate,
            "avg_prep_minutes": avg_prep_minutes,
            "p90_prep_minutes": p90_prep_minutes,
            "prep_completed_count": len(prep_durations),
            "avg_handoff_wait_minutes": avg_handoff_wait_minutes,
            "handoff_completed_count": len(handoff_waits),
            "review_count": review_count,
            "negative_review_count": negative_review_count,
            "delay_review_count": delay_review_count,
            "delay_review_event_ids": tuple(dict.fromkeys(delay_review_ids)),
            "source_event_ids": unique_source_ids,
        }
    )
