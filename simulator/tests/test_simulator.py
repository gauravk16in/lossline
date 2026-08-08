import os
import sys
# Add app/backend to path to resolve the app package imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "backend"))

import pytest
from datetime import datetime, timezone
from app.ingestion.schemas import EventEnvelope
from simulator.lossline_simulator.scenarios.lunch_rush import generate_scenario_events

def test_simulator_events_generation_and_validation():
    start_time = datetime.now(timezone.utc)
    seed = 42
    
    # 1. Generate events
    baseline, pre_approval, post_approval = generate_scenario_events(
        start_time=start_time,
        seed=seed
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

    # 4. Verify specific degradation event details (inventory stockout)
    stockout_found = False
    for ev in pre_approval:
        if ev["event_type"] == "inventory.updated" and ev["entity"]["id"] == "MEGHANA_SPECIAL_CHICKEN_BIRYANI":
            if ev["data"]["new_qty"] == 0.0:
                stockout_found = True
                assert ev["data"]["previous_qty"] > 0
                assert ev["data"]["unit"] == "kg"
                
    assert stockout_found, "MEGHANA_SPECIAL_CHICKEN_BIRYANI stockout event was not generated in the degradation phase."
