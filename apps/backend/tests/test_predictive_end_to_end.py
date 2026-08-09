from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from lossline_simulator.predictive_runner import run_predictive_demo
from src.db.models import Event, ForecastRecord, PredictiveDecisionRecord
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
    assert len(result["today"]["outcomes"]) == 3
    assert any(item["stockout_risk"] for item in result["today"]["inventory_projections"])
    assert {item["evaluation_type"] for item in result["evaluations"]} == {"FORECAST", "RISK", "DECISION"}
    assert await db_session.scalar(select(func.count(Event.id))) == 8
    assert await db_session.scalar(select(func.count(ForecastRecord.forecast_id))) == 3
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
