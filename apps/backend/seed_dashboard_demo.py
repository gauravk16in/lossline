"""Seed the dashboard through public API contracts using a persistent local database.

Run against Docker from the repository root:
    LOSSLINE_API_URL=http://localhost:8000 LOSSLINE_INGEST_KEY=demo-key \
      LOSSLINE_MANAGER_KEY=demo-key \
      PYTHONPATH=apps/backend:simulator .venv/bin/python apps/backend/seed_dashboard_demo.py

Or use a persistent local SQLite backend:
    DATABASE_URL=sqlite+aiosqlite:///apps/backend/lossline_demo.sqlite \
      INLINE_PROCESSING=true INGEST_API_KEY=demo-key MANAGER_API_KEY=demo-key \
      PYTHONPATH=apps/backend:simulator \
      .venv/bin/python apps/backend/seed_dashboard_demo.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
import random
from typing import Any

from httpx import ASGITransport, AsyncClient

from lossline_simulator.scenarios.predictive_demo import generate_predictive_demo_events
from src.db.models import Base
from src.db.session import engine
from src.main import app

INGEST_KEY = os.getenv("LOSSLINE_INGEST_KEY", "demo-key")
MANAGER_KEY = os.getenv("LOSSLINE_MANAGER_KEY", "demo-key")


SKU_PLANS = (
    ("CHICKEN_BIRYANI", 52, 45, 8.0),
    ("PANEER_BIRYANI", 41, 34, 7.0),
    ("VEG_FRIED_RICE", 38, 72, 6.0),
    ("MASALA_CHAAS", 25, 15, 2.0),
    ("GULAB_JAMUN", 31, 58, 3.0),
    ("DAL_MAKHANI", 33, 22, 6.0),
    ("HAKKA_NOODLES", 29, 55, 7.0),
    ("COLD_COFFEE", 41, 25, 3.0),
)


def enrich_event(event: dict[str, Any], *, seed: int, demand_scale: float = 1.0,
    service_window: str | None = None, duration_hours: int = 3,
    outlet_id: str = "meghana_indiranagar") -> dict[str, Any]:
    """Add the full menu to a canonical predictive input or observation."""
    result = event.copy()
    suffix = f"{outlet_id}_{service_window or 'default'}".lower()
    result["restaurant_id"] = outlet_id
    result["event_id"] = f"{event['event_id']}_{suffix}"
    result["entity"] = dict(event["entity"]) | {"id": f"{event['entity']['id']}_{suffix}"}
    data = dict(event["data"])
    if service_window:
        data["service_window"] = service_window
        window_start = datetime.fromisoformat(str(data["window_start"]))
        data["window_end"] = (window_start + timedelta(hours=duration_hours)).isoformat()
    rng = random.Random(f"{event['event_id']}:{seed}:dashboard.v1")
    scheduled = event["event_type"] == "predictive.window_scheduled"
    skus: list[dict[str, Any]] = []
    for sku_id, base, inventory, workload in SKU_PLANS:
        scaled_base = max(1, round(base * demand_scale))
        demand = max(0, round(scaled_base * rng.uniform(0.90, 1.16)))
        target_opening = inventory if demand_scale == 1.0 else max(scaled_base + 2, round(inventory * demand_scale))
        opening = target_opening if "schedule" in str(event["event_id"]) or "actual" in str(event["event_id"]) else round(scaled_base * rng.uniform(1.05, 1.35))
        if scheduled:
            skus.append({"sku_id": sku_id, "base_demand": float(scaled_base),
                "opening_inventory": opening, "replenishment_quantity": 0,
                "workload_minutes": workload})
        else:
            fulfilled = min(demand, opening)
            skus.append({"sku_id": sku_id, "actual_demand": demand,
                "fulfilled_quantity": fulfilled, "unfulfilled_quantity": demand - fulfilled,
                "ending_inventory": opening - fulfilled, "stockout": demand > opening,
                "workload_minutes": workload, "opening_inventory": opening})
    data["skus"] = skus
    result["data"] = data
    return result


async def post_event(client: AsyncClient, event: dict[str, object]) -> dict[str, object]:
    response = await client.post("/api/v1/events", json=event,
        headers={"X-LOSSLine-Key": INGEST_KEY})
    response.raise_for_status()
    return response.json()


async def seed_cycle(client: AsyncClient, *, seed: int, review: str | None, mature: bool,
    start: datetime | None = None, demand_scale: float = 1.0,
    service_window: str = "DINNER", duration_hours: int = 3,
    outlet_id: str = "meghana_indiranagar") -> None:
    start = start or datetime(2026, 8, 10, 13, tzinfo=timezone.utc) + timedelta(days=seed - 42)
    history, scheduled, actual = generate_predictive_demo_events(
        seed=seed, target_window_start=start
    )
    history = tuple(enrich_event(event, seed=seed, demand_scale=demand_scale,
        service_window=service_window, duration_hours=duration_hours,
        outlet_id=outlet_id) for event in history)
    scheduled = enrich_event(scheduled, seed=seed, demand_scale=demand_scale,
        service_window=service_window, duration_hours=duration_hours, outlet_id=outlet_id)
    actual = enrich_event(actual, seed=seed, demand_scale=demand_scale,
        service_window=service_window, duration_hours=duration_hours, outlet_id=outlet_id)
    for event in history:
        await post_event(client, event)
    scheduled_result = await post_event(client, scheduled)
    if scheduled_result.get("duplicate"):
        if mature:
            await post_event(client, actual)
        return
    cycle = scheduled_result["predictive"]
    if not isinstance(cycle, dict):
        raise RuntimeError("scheduled event did not produce a predictive cycle")
    if review:
        response = await client.post(
            f"/api/v1/predictive/decisions/{cycle['decision_id']}/review",
            headers={"X-LOSSLine-Key": MANAGER_KEY},
            json={
                "decision": review,
                "manager_id": "demo_manager",
                "idempotency_key": f"dashboard-seed-{outlet_id}-{service_window}-{seed}-{review.lower()}",
                "manager_note": "Seeded through the public manager-review API",
            },
        )
        response.raise_for_status()
    if mature:
        await post_event(client, actual)


async def main() -> None:
    api_url = os.getenv("LOSSLINE_API_URL")
    if api_url:
        client = AsyncClient(base_url=api_url, timeout=60)
    else:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://lossline.local",
            headers={"X-LOSSLine-Key": INGEST_KEY})
    async with client:
        profiles = {
            "BREAKFAST": ((0.18, 0.38, 0.62, 0.84, 0.68, 0.42),
                datetime(2026, 8, 16, 0, 30, tzinfo=timezone.utc)),  # 6 AM IST
            "DINNER": ((0.24, 0.42, 0.72, 0.96, 0.86, 0.58, 0.30),
                datetime(2026, 8, 16, 11, 30, tzinfo=timezone.utc)),  # 5 PM IST
        }
        for outlet_index, outlet_id in enumerate(("meghana_indiranagar", "meghana_hsr_layout")):
            for window_index, (service_window, (profile, start)) in enumerate(profiles.items()):
                base_seed = 200 + outlet_index * 100 + window_index * 30
                for offset, review in enumerate(("APPROVE", "REJECT", None)):
                    await seed_cycle(client, seed=base_seed + offset, outlet_id=outlet_id,
                        service_window=service_window,
                        start=start - timedelta(days=2 - offset),
                        demand_scale=1 + outlet_index * 0.12 + window_index * 0.08,
                        review=review, mature=review is not None)
                for index, scale in enumerate(profile):
                    await seed_cycle(client, seed=base_seed + 10 + index, review="APPROVE",
                        mature=index < 2, outlet_id=outlet_id,
                        start=start + timedelta(hours=index), demand_scale=scale,
                        service_window=f"{service_window}_HOURLY", duration_hours=1)
        today = (await client.get(
            "/api/v1/predictive/today/meghana_indiranagar/DINNER"
        )).json()
        print({
            "forecasts": len(today["forecasts"]),
            "risks": len(today["risks"]),
            "decisions": len(today["decisions"]),
            "outcomes": len(today["outcomes"]),
            "evaluations": len(today["evaluations"]),
        })
        hourly = (await client.get(
            "/api/v1/predictive/today/meghana_indiranagar/DINNER_HOURLY"
        )).json()
        print({"hourly_forecasts": len(hourly["forecasts"]),
            "hourly_windows": len({item["window_start"] for item in hourly["forecasts"]})})
    if not api_url:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
