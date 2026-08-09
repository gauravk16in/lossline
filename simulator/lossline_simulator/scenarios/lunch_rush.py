import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

RESTAURANT_ID = "meghana_indiranagar"
SCENARIO_ID = "meghana_lunch_rush_v1"

# Menu configuration
ITEMS = {
    "MEGHANA_SPECIAL_CHICKEN_BIRYANI": {"price": 320.0, "initial_qty": 60.0},
    "MEGHANA_MUTTON_BIRYANI": {"price": 420.0, "initial_qty": 30.0},
    "MEGHANA_ALOO_BIRYANI": {"price": 240.0, "initial_qty": 20.0},
}

CHANNELS = ["delivery", "dine_in", "takeaway"]


def create_event(
    event_id: str,
    source: str,
    event_type: str,
    occurred_at: datetime,
    entity_type: str,
    entity_id: str,
    data: Dict[str, Any],
    sequence: int,
) -> Dict[str, Any]:
    """
    Creates a canonical event dictionary matching the validation schema.
    """
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "restaurant_id": RESTAURANT_ID,
        "source": source,
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "entity": {"type": entity_type, "id": entity_id},
        "data": data,
        "metadata": {
            "synthetic": True,
            "scenario_id": SCENARIO_ID,
            "sequence": sequence,
        },
    }


def generate_scenario_events(
    start_time: datetime, seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates historical baseline, pre-approval live, and post-approval recovery events.
    """
    random.seed(seed)

    baseline_events: List[Dict[str, Any]] = []
    pre_approval_events: List[Dict[str, Any]] = []
    post_approval_events: List[Dict[str, Any]] = []

    seq_counter = 1

    # Normalize start time to UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time = start_time.astimezone(timezone.utc)

    # =========================================================================
    # PART 1: 7-DAY HISTORICAL BASELINE EVENTS
    # =========================================================================
    # Generates standard daily lunches (12:00 PM to 2:30 PM) for the past 7 days.
    for day in range(7, 0, -1):
        day_start = start_time - timedelta(days=day)
        # Generate normal orders (12:00 PM to 2:00 PM)
        # Average 25 orders per day, normal wait times, zero/low cancellations
        lunch_time = day_start.replace(hour=12, minute=0, second=0, microsecond=0)
        for order_idx in range(25):
            order_time = lunch_time + timedelta(minutes=int(random.uniform(0, 120)))
            ord_id = f"ord_base_{day}_{order_idx}"
            sku = random.choice(list(ITEMS.keys()))
            price = ITEMS[sku]["price"]
            channel = random.choice(CHANNELS)

            # Order created
            baseline_events.append(
                create_event(
                    event_id=f"evt_base_oc_{day}_{order_idx}",
                    source="pos",
                    event_type="order.created",
                    occurred_at=order_time,
                    entity_type="order",
                    entity_id=ord_id,
                    data={"channel": channel, "amount": price, "currency": "INR"},
                    sequence=seq_counter,
                )
            )
            seq_counter += 1

            # Order completed (with normal wait times, e.g. 15-25 minutes)
            wait_sec = random.uniform(900, 1500)
            complete_time = order_time + timedelta(seconds=int(wait_sec))

            baseline_events.append(
                create_event(
                    event_id=f"evt_base_prep_{day}_{order_idx}",
                    source="kds",
                    event_type="preparation.completed",
                    occurred_at=complete_time,
                    entity_type="order",
                    entity_id=ord_id,
                    data={"order_id": ord_id, "duration_seconds": wait_sec},
                    sequence=seq_counter,
                )
            )
            seq_counter += 1

            # Handoff completed (if delivery channel)
            if channel == "delivery":
                handoff_wait = random.uniform(120, 240)
                baseline_events.append(
                    create_event(
                        event_id=f"evt_base_del_{day}_{order_idx}",
                        source="delivery",
                        event_type="delivery.handoff_completed",
                        occurred_at=complete_time
                        + timedelta(seconds=int(handoff_wait)),
                        entity_type="order",
                        entity_id=ord_id,
                        data={"order_id": ord_id, "wait_seconds": handoff_wait},
                        sequence=seq_counter,
                    )
                )
                seq_counter += 1

    # =========================================================================
    # PART 2: LIVE PRE-APPROVAL EVENTS (Healthy -> Surge -> Degradation)
    # =========================================================================
    live_start = start_time.replace(hour=12, minute=0, second=0, microsecond=0)

    # --- PHASE A: Healthy Phase (Minute 0 to 15) ---
    # 5 normal orders completed successfully
    for idx in range(5):
        order_time = live_start + timedelta(minutes=idx * 3)
        ord_id = f"ord_live_healthy_{idx}"
        sku = "MEGHANA_SPECIAL_CHICKEN_BIRYANI"
        price = ITEMS[sku]["price"]

        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_oc_{idx}",
                source="pos",
                event_type="order.created",
                occurred_at=order_time,
                entity_type="order",
                entity_id=ord_id,
                data={"channel": "delivery", "amount": price, "currency": "INR"},
                sequence=seq_counter,
            )
        )
        seq_counter += 1

        # Handoff normal wait
        handoff_time = order_time + timedelta(minutes=15)
        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_del_{idx}",
                source="delivery",
                event_type="delivery.handoff_completed",
                occurred_at=handoff_time,
                entity_type="order",
                entity_id=ord_id,
                data={"order_id": ord_id, "wait_seconds": 180.0},
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # --- PHASE B: Demand Surge Phase (Minute 15 to 45) ---
    # A massive wave of delivery orders arrives (20 orders in 30 minutes)
    for idx in range(20):
        order_time = live_start + timedelta(minutes=15) + timedelta(seconds=idx * 90)
        ord_id = f"ord_live_surge_{idx}"
        sku = "MEGHANA_SPECIAL_CHICKEN_BIRYANI"
        price = ITEMS[sku]["price"]

        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_oc_surge_{idx}",
                source="pos",
                event_type="order.created",
                occurred_at=order_time,
                entity_type="order",
                entity_id=ord_id,
                data={"channel": "delivery", "amount": price, "currency": "INR"},
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # --- PHASE C: Degradation Phase (Minute 45 to 65) ---
    # 1. Handoff wait times spike for completed deliveries (3 completed with high wait)
    degrade_start = live_start + timedelta(minutes=45)
    for idx in range(3):
        complete_time = degrade_start + timedelta(minutes=idx * 5)
        ord_id = f"ord_live_surge_{idx}"
        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_del_deg_{idx}",
                source="delivery",
                event_type="delivery.handoff_completed",
                occurred_at=complete_time,
                entity_type="order",
                entity_id=ord_id,
                data={
                    "order_id": ord_id,
                    "wait_seconds": 950.0,
                },  # Wait time > 15 minutes!
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # Preparation time is required evidence for the overload rule.
    for idx in range(6):
        prep_time = degrade_start + timedelta(minutes=idx * 2)
        ord_id = f"ord_live_surge_{idx}"
        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_prep_deg_{idx}",
                source="kds",
                event_type="preparation.completed",
                occurred_at=prep_time,
                entity_type="order",
                entity_id=ord_id,
                data={"order_id": ord_id, "duration_seconds": 2700.0},
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # Order cancellations surge due to preparation delays.
    for idx in range(5):
        cancel_time = degrade_start + timedelta(minutes=7) + timedelta(minutes=idx * 2)
        ord_id = f"ord_live_surge_{idx + 5}"
        price = ITEMS["MEGHANA_SPECIAL_CHICKEN_BIRYANI"]["price"]
        reason = "PREPARATION_DELAY"

        pre_approval_events.append(
            create_event(
                event_id=f"evt_live_oc_cancel_{idx}",
                source="pos",
                event_type="order.cancelled",
                occurred_at=cancel_time,
                entity_type="order",
                entity_id=ord_id,
                data={
                    "channel": "delivery",
                    "amount": price,
                    "currency": "INR",
                    "reason_code": reason,
                },
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # 4. Negative customer reviews start arriving (2 bad reviews)
    pre_approval_events.append(
        create_event(
            event_id="evt_live_review_1",
            source="reviews",
            event_type="review.received",
            occurred_at=degrade_start + timedelta(minutes=12),
            entity_type="restaurant",
            entity_id=RESTAURANT_ID,
            data={
                "rating": 1,
                "text": "My biryani delivery has been delayed for over 45 minutes! Horrible lunch service.",
                "language": "en",
            },
            sequence=seq_counter,
        )
    )
    seq_counter += 1

    pre_approval_events.append(
        create_event(
            event_id="evt_live_review_2",
            source="reviews",
            event_type="review.received",
            occurred_at=degrade_start + timedelta(minutes=18),
            entity_type="restaurant",
            entity_id=RESTAURANT_ID,
            data={
                "rating": 2,
                "text": "They cancelled my order because the Chicken Biryani was out of stock. Very disappointed.",
                "language": "en",
            },
            sequence=seq_counter,
        )
    )
    seq_counter += 1

    # =========================================================================
    # PART 3: RECOVERY PHASE EVENTS (Triggered only AFTER manager approval)
    # =========================================================================
    # Generates events representing recovery (order volume decreases, wait times normalize)
    recovery_start = degrade_start + timedelta(minutes=20)

    # Simulate remaining queue completions with normal wait times
    for idx in range(10):
        comp_time = recovery_start + timedelta(minutes=idx * 2)
        ord_id = f"ord_live_surge_{idx + 10}"

        post_approval_events.append(
            create_event(
                event_id=f"evt_rec_order_{idx}",
                source="pos",
                event_type="order.created",
                occurred_at=comp_time - timedelta(minutes=12),
                entity_type="order",
                entity_id=ord_id,
                data={"channel": "delivery", "amount": 320.0, "currency": "INR"},
                sequence=seq_counter,
            )
        )
        seq_counter += 1
        post_approval_events.append(
            create_event(
                event_id=f"evt_rec_prep_{idx}",
                source="kds",
                event_type="preparation.completed",
                occurred_at=comp_time - timedelta(minutes=2),
                entity_type="order",
                entity_id=ord_id,
                data={"order_id": ord_id, "duration_seconds": 600.0},
                sequence=seq_counter,
            )
        )
        seq_counter += 1

        # Complete remaining orders successfully
        post_approval_events.append(
            create_event(
                event_id=f"evt_rec_del_{idx}",
                source="delivery",
                event_type="delivery.handoff_completed",
                occurred_at=comp_time,
                entity_type="order",
                entity_id=ord_id,
                data={
                    "order_id": ord_id,
                    "wait_seconds": 150.0,
                },  # Handoff delay normalized
                sequence=seq_counter,
            )
        )
        seq_counter += 1

    # Ingest a positive review demonstrating recovery
    post_approval_events.append(
        create_event(
            event_id="evt_rec_review",
            source="reviews",
            event_type="review.received",
            occurred_at=recovery_start + timedelta(minutes=25),
            entity_type="restaurant",
            entity_id=RESTAURANT_ID,
            data={
                "rating": 5,
                "text": "Order was fulfilled quickly, issues seem resolved now.",
                "language": "en",
            },
            sequence=seq_counter,
        )
    )
    seq_counter += 1

    return baseline_events, pre_approval_events, post_approval_events
