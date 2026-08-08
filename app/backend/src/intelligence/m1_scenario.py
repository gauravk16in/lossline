"""Shared M1 lunch-rush overload event payloads for demos and tests.

Seed targets (vs fixture baseline: orders=18, prep=12m, cancel=7%):
  - >=24 order.created  → ORDER_VOLUME_SPIKE (ratio >=1.3x and robust z>=2)
  - >=8 preparation.completed at ~20min → PREP_TIME_SPIKE (>=1.4x of 12m)
  - >=5 order.cancelled → CANCELLATION_SPIKE (>=2x of 7% and gap>=5pp)
  - optional handoff / delay reviews as supporting signals
"""

from __future__ import annotations

from typing import Any

OUTLET = "store_17"
WINDOW_TS = "2026-08-08T12:10:00Z"
CANCEL_TS = "2026-08-08T12:20:00Z"
PREP_TS = "2026-08-08T12:15:00Z"
HANDOFF_TS = "2026-08-08T12:18:00Z"
REVIEW_TS = "2026-08-08T12:25:00Z"

ORDER_COUNT = 24
PREP_COUNT = 8
CANCEL_COUNT = 5
HANDOFF_COUNT = 8
# Prep duration: 20 minutes = 1200s (baseline fixture = 12m → ~1.67x)
PREP_DURATION_SECONDS = 1200.0
# Handoff wait: 6 minutes = 360s (baseline fixture = 3m → 2.0x)
HANDOFF_WAIT_SECONDS = 360.0


def order_created(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_m1_ord_{i:03d}",
        "restaurant_id": OUTLET,
        "source": "pos",
        "event_type": "order.created",
        "occurred_at": WINDOW_TS,
        "entity": {"type": "order", "id": f"ord_m1_{i:03d}"},
        "data": {"channel": "delivery", "amount": 500.0, "currency": "INR"},
        "metadata": {"synthetic": True, "scenario_id": "m1_overload"},
    }


def preparation_completed(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_m1_prep_{i:03d}",
        "restaurant_id": OUTLET,
        "source": "kds",
        "event_type": "preparation.completed",
        "occurred_at": PREP_TS,
        "entity": {"type": "order", "id": f"ord_m1_{i:03d}"},
        "data": {
            "order_id": f"ord_m1_{i:03d}",
            "duration_seconds": PREP_DURATION_SECONDS,
        },
        "metadata": {"synthetic": True, "scenario_id": "m1_overload"},
    }


def order_cancelled(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_m1_cancel_{i:03d}",
        "restaurant_id": OUTLET,
        "source": "pos",
        "event_type": "order.cancelled",
        "occurred_at": CANCEL_TS,
        "entity": {"type": "order", "id": f"ord_m1_{i:03d}"},
        "data": {
            "channel": "delivery",
            "amount": 500.0,
            "currency": "INR",
            "reason_code": "TOO_LONG",
        },
        "metadata": {"synthetic": True, "scenario_id": "m1_overload"},
    }


def handoff_completed(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_m1_handoff_{i:03d}",
        "restaurant_id": OUTLET,
        "source": "delivery",
        "event_type": "delivery.handoff_completed",
        "occurred_at": HANDOFF_TS,
        "entity": {"type": "order", "id": f"ord_m1_{i:03d}"},
        "data": {
            "order_id": f"ord_m1_{i:03d}",
            "wait_seconds": HANDOFF_WAIT_SECONDS,
        },
        "metadata": {"synthetic": True, "scenario_id": "m1_overload"},
    }


def delay_review(i: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": f"evt_m1_review_{i:03d}",
        "restaurant_id": OUTLET,
        "source": "reviews",
        "event_type": "review.received",
        "occurred_at": REVIEW_TS,
        "entity": {"type": "review", "id": f"rev_m1_{i:03d}"},
        "data": {
            "rating": 1,
            "text": "Food was late and cold, long wait",
            "language": "en",
        },
        "metadata": {"synthetic": True, "scenario_id": "m1_overload"},
    }


def m1_overload_payloads(*, include_supporting: bool = True) -> list[dict[str, Any]]:
    """Full event set for one 30-min lunch-rush overload window."""
    payloads: list[dict[str, Any]] = []
    for i in range(1, ORDER_COUNT + 1):
        payloads.append(order_created(i))
    for i in range(1, PREP_COUNT + 1):
        payloads.append(preparation_completed(i))
    for i in range(1, CANCEL_COUNT + 1):
        payloads.append(order_cancelled(i))
    if include_supporting:
        for i in range(1, HANDOFF_COUNT + 1):
            payloads.append(handoff_completed(i))
        for i in range(1, 3):
            payloads.append(delay_review(i))
    return payloads


def m1_trigger_payload() -> dict[str, Any]:
    """Last cancel event used to kick the detection pipeline."""
    return order_cancelled(CANCEL_COUNT)
