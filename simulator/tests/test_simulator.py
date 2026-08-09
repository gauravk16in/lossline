import os
import sys

# Add the canonical backend package to the import path.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "apps", "backend"))
sys.path.insert(0, os.path.join(ROOT, "simulator"))

import pytest
from datetime import datetime, timezone
from src.ingestion.schemas import EventEnvelope
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
