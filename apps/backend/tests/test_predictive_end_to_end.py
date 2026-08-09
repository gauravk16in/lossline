from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from lossline_simulator.predictive_runner import run_predictive_demo
from lossline_intelligence.features.catalog import build_demo_registry
from src.db.models import Event, ForecastRecord, PredictiveDecisionRecord, PredictiveFeatureSnapshot
from src.main import app

START = datetime(2026, 9, 9, 13, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_seeded_predictive_demo_uses_events_and_closes_loop(client_override, db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/demo/reset")).status_code == 200
        result = await run_predictive_demo(api_url="", seed=42, target_window_start=START, client=client)

    assert result["history_event_count"] == 6
    assert len(result["cycle"]["forecast_ids"]) == 3
    assert result["review"]["status"] == "MANAGER_APPROVED"
    assert len(result["outcome_ids"]) == 3
    assert len(result["today"]["forecasts"]) == 3
    assert len(result["today"]["capacity_projections"]) == 1
    assert result["today"]["capacity_projections"][0]["projection_id"] in {
        ref["artifact_id"] for ref in result["today"]["dossiers"][0]["capacity_refs"]
    }
    assert result["today"]["dossiers"][0]["similar_periods"]
    assert result["today"]["dossiers"][0]["historical_performance"]
    chicken_snapshot = next(item for item in result["today"]["feature_snapshots"]
        if item["sku_id"] == "CHICKEN_BIRYANI")
    assert chicken_snapshot["feature_values"] == {
        "context.weekday": 5,
        "context.service_window": "DINNER",
        "context.is_holiday": False,
        "context.local_event": False,
        "context.delivery_share": "0.6800",
        "context.data_quality": "1.0000",
        "weather.state": "RAIN",
        "weather.rainfall_mm": "18.0000",
        "promotion.active": True,
        "promotion.discount_pct": "0.2000",
        "inventory.opening_quantity": 45,
        "capacity.available_minutes": "1000.0000",
        "demand.fulfilled_quantity.lag1": 51,
        "sku.base_demand": "52.0000",
        "sku.workload_minutes": "8.0000",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        feature_response = await client.get(
            f"/api/v1/predictive/features/{chicken_snapshot['snapshot_id']}")
    assert feature_response.status_code == 200
    assert feature_response.json()["fingerprint"] == chicken_snapshot["fingerprint"]
    assert len(result["today"]["outcomes"]) == 3
    assert any(item["stockout_risk"] for item in result["today"]["inventory_projections"])
    assert {item["evaluation_type"] for item in result["evaluations"]} == {"FORECAST", "RISK", "DECISION"}
    assert await db_session.scalar(select(func.count(Event.id))) == 8
    assert await db_session.scalar(select(func.count(ForecastRecord.forecast_id))) == 3
    snapshots = (await db_session.execute(select(PredictiveFeatureSnapshot))).scalars().all()
    registry = build_demo_registry()
    assert {row.payload["registry_fingerprint"] for row in snapshots} == {registry.fingerprint}
    assert all(set(row.payload["feature_values"]) == {
        definition.feature_id for definition in registry.definitions
    } for row in snapshots)
    decision = (await db_session.execute(select(PredictiveDecisionRecord))).scalars().one()
    assert decision.status == "MANAGER_APPROVED"


@pytest.mark.asyncio
async def test_identical_seed_replays_identical_artifact_ids(client_override) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/demo/reset")
        first = await run_predictive_demo(api_url="", seed=77, target_window_start=START, client=client)
        await client.post("/api/v1/demo/reset")
        second = await run_predictive_demo(api_url="", seed=77, target_window_start=START, client=client)
    assert first["cycle"] == second["cycle"]
    assert first["outcome_ids"] == second["outcome_ids"]
