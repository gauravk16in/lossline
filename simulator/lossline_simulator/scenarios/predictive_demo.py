"""C22 seeded predictive demo events; contains inputs/actuals, never forecasts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..causal_world import GoldenScenario, SKU_CONFIGS, SyntheticWindow, generate_window

PREDICTIVE_DEMO_SCENARIO_ID = "predictive_stockout_v1"


def _context(window: SyntheticWindow) -> dict[str, Any]:
    context = window.context
    return {
        "weekday": context.weekday,
        "weather_state": context.weather.value,
        "rainfall_mm": None if context.rainfall_mm is None else float(context.rainfall_mm),
        "holiday": context.holiday,
        "local_event": context.local_event,
        "promoted_sku_id": context.promoted_sku_id,
        "promotion_discount": None if context.promotion_discount is None else float(context.promotion_discount),
        "delivery_share": float(context.delivery_share),
    }


def _envelope(*, event_id: str, occurred_at: datetime, event_type: str,
    entity_id: str, data: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {"schema_version": "1.0", "event_id": event_id,
        "restaurant_id": "meghana_indiranagar", "source": "simulator",
        "event_type": event_type, "occurred_at": occurred_at.astimezone(timezone.utc).isoformat(),
        "entity": {"type": "predictive_window", "id": entity_id}, "data": data,
        "metadata": {"synthetic": True, "scenario_id": PREDICTIVE_DEMO_SCENARIO_ID,
            "sequence": sequence, "schema_version": "1.0"}}


def _observed_data(window: SyntheticWindow) -> dict[str, Any]:
    workload_by_sku = {item.sku_id: item.workload_minutes for item in SKU_CONFIGS}
    return {"service_window": window.context.service_window,
        "window_start": window.window_start.isoformat(), "window_end": window.window_end.isoformat(),
        "capacity_utilization": float(window.capacity_utilization),
        "available_capacity_minutes": float(window.available_capacity_minutes),
        "data_quality": float(window.context.data_quality), "context": _context(window),
        "skus": [{"sku_id": item.sku_id, "actual_demand": item.latent_demand_quantity,
            "fulfilled_quantity": item.fulfilled_quantity, "unfulfilled_quantity": item.unfulfilled_quantity,
            "ending_inventory": item.ending_inventory_quantity, "stockout": item.stockout,
            "workload_minutes": float(workload_by_sku[item.sku_id]),
            "opening_inventory": item.opening_inventory_quantity} for item in window.sku_outcomes]}


def generate_predictive_demo_events(*, seed: int, target_window_start: datetime) -> tuple[tuple[dict[str, Any], ...], dict[str, Any], dict[str, Any]]:
    """Return history, scheduled-input and later-actual envelopes in posting order."""
    if target_window_start.tzinfo is None or target_window_start.utcoffset() is None:
        raise ValueError("target_window_start must be timezone-aware")
    target_start = target_window_start.astimezone(timezone.utc)
    history: list[dict[str, Any]] = []
    sequence = 1
    for weeks_back in range(6, 0, -1):
        window = generate_window(GoldenScenario.NORMAL_WEEKDAY, seed=seed + weeks_back,
            window_start=target_start - timedelta(days=7 * weeks_back))
        history.append(_envelope(event_id=f"pred_hist_{weeks_back}_{seed}",
            occurred_at=window.window_end + timedelta(minutes=30),
            event_type="demand.window_observed", entity_id=f"hist_{weeks_back}",
            data=_observed_data(window), sequence=sequence))
        sequence += 1
    target = generate_window(GoldenScenario.PROMOTION_LIMITED_INVENTORY, seed=seed,
        window_start=target_start)
    workload_by_sku = {item.sku_id: item.workload_minutes for item in SKU_CONFIGS}
    scheduled_data = {"service_window": target.context.service_window,
        "window_start": target.window_start.isoformat(), "window_end": target.window_end.isoformat(),
        "available_capacity_minutes": float(target.available_capacity_minutes),
        "data_quality": float(target.context.data_quality), "context": _context(target),
        "skus": [{"sku_id": item.sku_id, "base_demand": float(item.baseline_demand),
            "opening_inventory": item.opening_inventory_quantity, "replenishment_quantity": 0,
            "workload_minutes": float(workload_by_sku[item.sku_id])} for item in target.sku_outcomes]}
    scheduled = _envelope(event_id=f"pred_schedule_{seed}",
        occurred_at=target.window_start - timedelta(hours=1),
        event_type="predictive.window_scheduled", entity_id=f"target_{seed}",
        data=scheduled_data, sequence=sequence)
    actual = _envelope(event_id=f"pred_actual_{seed}",
        occurred_at=target.window_end + timedelta(minutes=30),
        event_type="demand.window_observed", entity_id=f"target_{seed}",
        data=_observed_data(target), sequence=sequence + 1)
    return tuple(history), scheduled, actual
