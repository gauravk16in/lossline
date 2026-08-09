from datetime import datetime, timezone

from lossline_simulator.scenarios.predictive_demo import generate_predictive_demo_events


START = datetime(2026, 9, 9, 13, tzinfo=timezone.utc)


def test_seeded_events_are_repeatable_and_ordered() -> None:
    first = generate_predictive_demo_events(seed=42, target_window_start=START)
    assert first == generate_predictive_demo_events(seed=42, target_window_start=START)
    history, scheduled, actual = first
    assert len(history) == 6
    assert all(item["event_type"] == "demand.window_observed" for item in history)
    assert scheduled["event_type"] == "predictive.window_scheduled"
    assert actual["event_type"] == "demand.window_observed"


def test_schedule_contains_inputs_not_model_outputs_or_target_actuals() -> None:
    _, scheduled, _ = generate_predictive_demo_events(seed=42, target_window_start=START)
    serialized = str(scheduled).lower()
    for prohibited in ("forecast_id", "point_demand", "lower_demand", "upper_demand",
        "actual_demand", "fulfilled_quantity", "unfulfilled_quantity"):
        assert prohibited not in serialized
    assert scheduled["data"]["skus"][0]["opening_inventory"] == 45


def test_actual_conserves_demand_and_all_events_use_canonical_envelope() -> None:
    history, scheduled, actual = generate_predictive_demo_events(seed=7, target_window_start=START)
    for event in (*history, scheduled, actual):
        assert set(event) == {"schema_version", "event_id", "restaurant_id", "source",
            "event_type", "occurred_at", "entity", "data", "metadata"}
        assert event["source"] == "simulator"
    for sku in actual["data"]["skus"]:
        assert sku["fulfilled_quantity"] + sku["unfulfilled_quantity"] == sku["actual_demand"]
