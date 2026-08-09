import os
import sys

# Add the canonical backend package to the import path.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "apps", "backend"))
sys.path.insert(0, os.path.join(ROOT, "simulator"))

import pytest
from datetime import datetime, timezone
from src.ingestion.schemas import EventEnvelope
from src.intelligence.mapper import envelope_to_normalized
from lossline_intelligence.aggregation import build_metric_snapshot
from lossline_simulator.scenarios.lunch_rush import generate_scenario_events


def test_simulator_events_generation_and_validation():
    start_time = datetime.now(timezone.utc)
    seed = 42

    # 1. Generate events
    baseline, pre_approval, post_approval = generate_scenario_events(
        start_time=start_time, seed=seed
    )

    # Verify lists are not empty
    assert len(baseline) > 0
    assert len(pre_approval) > 0
    assert len(post_approval) > 0

    # 2. Strict validation check
    # Iterate through all generated events and parse them into the backend's EventEnvelope schema
    # If any event fails to validate, an exception will be raised, failing the test.
    all_events = baseline + pre_approval + post_approval
    for ev in all_events:
        envelope = EventEnvelope(**ev)
        assert envelope.restaurant_id == "meghana_indiranagar"
        assert envelope.schema_version == "1.0"

    # 3. Check baseline events are in the past
    for ev in baseline:
        occurred_at = datetime.fromisoformat(ev["occurred_at"])
        assert occurred_at < start_time

    required = {"order.created", "preparation.completed", "order.cancelled"}
    assert required.issubset({event["event_type"] for event in pre_approval})
    assert any(event["event_type"] == "order.created" for event in post_approval)
    assert generate_scenario_events(start_time=start_time, seed=seed) == (
        baseline,
        pre_approval,
        post_approval,
    )


def test_actual_lunch_rush_has_all_required_evidence_in_one_window():
    start = datetime(2026, 8, 10, 1, 0, tzinfo=timezone.utc)
    _, live, _ = generate_scenario_events(start_time=start, seed=42, scenario_run_id="run-42")
    window_start = start.replace(hour=12, minute=30, second=0, microsecond=0)
    snapshot = build_metric_snapshot(
        [envelope_to_normalized(EventEnvelope(**event)) for event in live],
        outlet_id="meghana_indiranagar",
        window_start=window_start,
        window_end=window_start.replace(hour=13, minute=0),
    )
    assert snapshot.order_count >= 24
    assert snapshot.prep_completed_count >= 8
    assert snapshot.cancelled_order_count >= 5
    assert all(event["metadata"]["scenario_run_id"] == "run-42" for event in live)
