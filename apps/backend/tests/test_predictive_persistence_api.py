from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from lossline_intelligence.attribution import AttributionInput, AttributionMethod, attribute_drivers
from lossline_intelligence.capacity import project_capacity
from lossline_intelligence.decisioning import (
    ActionRisk, DecisionAction, DecisionCandidate, DecisionPolicy, RiskType, Urgency, guard_decision,
)
from lossline_intelligence.dossiers import ArtifactRef, DataQualitySummary, build_forecast_dossier
from lossline_intelligence.features.snapshot import FeatureSnapshot, SnapshotQuality
from lossline_intelligence.forecasts.gbt import GBTForecast
from lossline_intelligence.inventory import project_inventory
from lossline_intelligence.outcomes import (
    ActualOutcomeStatus, evaluate_decision_outcome, evaluate_forecast_outcome, mature_actual_outcome,
)
from src.db.models import ForecastModelArtifactRecord, Restaurant
from src.intelligence.predictive_persistence import (
    persist_capacity_projection, persist_dossier, persist_driver, persist_feature_snapshot,
    persist_forecast, persist_guarded_decision, persist_inventory_projection,
    persist_risk_candidate, persist_decision_trace, select_forecast_strategy,
    persist_actual_outcome, persist_predictive_evaluation,
)
from src.main import app

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc); T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc); T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def artifacts():
    snapshot = FeatureSnapshot(snapshot_id="snap1", pipeline_version="v1", prediction_as_of=T0,
        outlet_id="out1", sku_id="sku1", service_window="DINNER", window_start=T1, window_end=T2,
        registry_version="r1", registry_fingerprint="rf1", feature_values={"sku.base_demand": Decimal("50")},
        missing_features=(), imputed_features=(), quality=SnapshotQuality(completeness=Decimal("1"), data_sufficiency=True),
        fingerprint="fp1", created_at=T0)
    forecast = GBTForecast(forecast_id="fc1", model_version="m1", artifact_id="art1",
        interval_method="empirical", prediction_as_of=T0, outlet_id="out1", sku_id="sku1",
        service_window="DINNER", window_start=T1, window_end=T2, feature_snapshot_id="snap1",
        point_demand=Decimal("50"), lower_demand=Decimal("40"), upper_demand=Decimal("65"), data_sufficient=True)
    inventory = project_inventory(forecast, opening_inventory=40, evidence_ids=("snap1",))
    capacity = project_capacity(forecast_id="fc1", outlet_id="out1", service_window="DINNER",
        window_start=T1, window_end=T2, sku_workloads=((Decimal("50"), Decimal("40"), Decimal("65"), Decimal("8")),),
        available_capacity_minutes=Decimal("500"), evidence_ids=("fc1",))
    driver = attribute_drivers(forecast_id="fc1", registered_feature_ids=("sku.base_demand",),
        candidates=(AttributionInput("sku.base_demand", "snap1", Decimal("1"), AttributionMethod.DETERMINISTIC_DEVIATION),))[0]
    dossier = build_forecast_dossier(outlet_id="out1", service_window="DINNER", window_start=T1,
        window_end=T2, prediction_as_of=T0, forecast_refs=(ArtifactRef(artifact_id="fc1", artifact_type="forecast", version="m1"),),
        feature_snapshot_refs=(ArtifactRef(artifact_id="snap1", artifact_type="snapshot", version="v1"),),
        inventory_refs=(ArtifactRef(artifact_id=inventory.projection_id, artifact_type="inventory", version="v1"),),
        capacity_refs=(ArtifactRef(artifact_id=capacity.projection_id, artifact_type="capacity", version="v1"),),
        driver_refs=(ArtifactRef(artifact_id=driver.driver_id, artifact_type="driver", version="v1"),),
        data_quality=DataQualitySummary(tier="HIGH"), provenance_ids=("snap1",))
    decision = DecisionCandidate(decision_id="dec1", decision_version="v1", dossier_id=dossier.dossier_id,
        forecast_id="fc1", outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        risk_type=RiskType.INVENTORY_SHORTAGE, sku_id="sku1", action=DecisionAction.ADJUST_PREP_QUANTITY,
        quantity=Decimal("10"), unit="portions", execute_by=T1, reason_code="SHORTAGE",
        evidence_ids=(driver.driver_id,), urgency=Urgency.HIGH, action_risk=ActionRisk.MEDIUM, approval_required=True)
    guard = guard_decision(candidate=decision, dossier=dossier, policy=DecisionPolicy(policy_id="p1",
        allowed_actions=(DecisionAction.ADJUST_PREP_QUANTITY,), max_prep_quantity=Decimal("10")))
    return snapshot, forecast, inventory, capacity, driver, dossier, decision, guard


async def persist_all(db):
    db.add(Restaurant(id="out1", name="Outlet 1", synthetic=True)); await db.flush()
    snapshot, forecast, inventory, capacity, driver, dossier, decision, guard = artifacts()
    await persist_feature_snapshot(db, snapshot); await persist_forecast(db, forecast)
    await persist_inventory_projection(db, inventory); await persist_capacity_projection(db, capacity)
    await persist_driver(db, driver); await persist_dossier(db, dossier)
    await persist_guarded_decision(db, decision, guard)
    return artifacts()


@pytest.mark.asyncio
async def test_immutable_persistence_is_idempotent_and_collision_safe(db_session) -> None:
    snapshot, forecast, *_ = await persist_all(db_session)
    assert (await persist_feature_snapshot(db_session, snapshot)).snapshot_id == "snap1"
    changed = forecast.model_copy(update={"point_demand": Decimal("51")})
    with pytest.raises(ValueError, match="immutable artifact collision"):
        await persist_forecast(db_session, changed)


@pytest.mark.asyncio
async def test_predictive_read_apis_and_404s(client_override, db_session) -> None:
    _, forecast, inventory, capacity, _, dossier, *_ = await persist_all(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/predictive/forecasts/out1/DINNER")).json()[0]["forecast_id"] == forecast.forecast_id
        assert (await client.get(f"/api/v1/predictive/projections/inventory/{inventory.projection_id}")).status_code == 200
        assert (await client.get(f"/api/v1/predictive/projections/capacity/{capacity.projection_id}")).status_code == 200
        assert (await client.get(f"/api/v1/predictive/dossiers/{dossier.dossier_id}")).status_code == 200
        today = await client.get("/api/v1/predictive/today/out1/DINNER")
        assert today.status_code == 200 and today.json()["forecasts"][0]["forecast_id"] == "fc1"
        assert len(today.json()["drivers"]) == 1 and len(today.json()["decisions"]) == 1
        assert (await client.get("/api/v1/predictive/dossiers/missing")).status_code == 404


@pytest.mark.asyncio
async def test_manager_review_idempotency_and_conflict(client_override, db_session) -> None:
    *_, decision, _ = await persist_all(db_session)
    url = f"/api/v1/predictive/decisions/{decision.decision_id}/review"
    payload = {"decision": "APPROVE", "manager_id": "manager1", "idempotency_key": "key1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(url, json=payload); second = await client.post(url, json=payload)
        assert first.status_code == 200 and first.json()["status"] == "MANAGER_APPROVED"
        assert second.json()["duplicate"] is True
        assert (await client.post(url, json=payload | {"decision": "REJECT"})).status_code == 409


@pytest.mark.asyncio
async def test_model_strategy_requires_accepted_artifact(db_session) -> None:
    assert (await select_forecast_strategy(db_session))["strategy"] == "BASELINE"
    db_session.add(ForecastModelArtifactRecord(artifact_id="art1", model_version="m1", accepted=False,
        training_cutoff=T0, checksum="c1", payload={}))
    await db_session.flush(); assert (await select_forecast_strategy(db_session))["strategy"] == "BASELINE"
    row = (await db_session.execute(select(ForecastModelArtifactRecord))).scalars().one(); row.accepted = True
    await db_session.flush(); assert (await select_forecast_strategy(db_session))["strategy"] == "GBT"


@pytest.mark.asyncio
async def test_risk_and_trace_are_immutable(db_session) -> None:
    *_, dossier, decision, guard = await persist_all(db_session)
    risk = {"risk_id": "risk1", "outlet_id": "out1", "forecast_id": "fc1",
        "risk_type": "INVENTORY_SHORTAGE", "severity": "HIGH", "evidence_ids": ["snap1"]}
    assert (await persist_risk_candidate(db_session, risk)).risk_id == "risk1"
    trace = {"trace_id": "trace1", "dossier_id": dossier.dossier_id,
        "decision_id": decision.decision_id, "guard_result_id": guard.guard_result_id,
        "checkpoint_thread_id": "thread1"}
    assert (await persist_decision_trace(db_session, trace)).trace_id == "trace1"
    with pytest.raises(ValueError, match="collision"):
        await persist_risk_candidate(db_session, risk | {"severity": "LOW"})


@pytest.mark.asyncio
async def test_matured_outcome_and_evaluation_persistence_api(client_override, db_session) -> None:
    _, forecast, *_, decision, _ = await persist_all(db_session)
    outcome = mature_actual_outcome(forecast=forecast, now=T2.replace(hour=17),
        actual_demand=Decimal("55"), fulfilled_quantity=Decimal("50"),
        unfulfilled_quantity=Decimal("5"), ending_inventory=Decimal("0"),
        capacity_utilization=Decimal("1.1"), status=ActualOutcomeStatus.AVAILABLE,
        source_ids=("event1",))
    await persist_actual_outcome(db_session, outcome)
    forecast_eval = evaluate_forecast_outcome(forecast, outcome)
    await persist_predictive_evaluation(db_session, evaluation_type="FORECAST",
        forecast_id="fc1", outcome_id=outcome.outcome_id, evaluation=forecast_eval)
    decision_eval = evaluate_decision_outcome(decision_id="dec1", manager_decision="APPROVE", outcome=outcome)
    await persist_predictive_evaluation(db_session, evaluation_type="DECISION",
        forecast_id="fc1", outcome_id=outcome.outcome_id, decision_id="dec1", evaluation=decision_eval)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/predictive/outcomes/fc1")).json()["actual_demand"] == "55.0000"
        evaluations = (await client.get("/api/v1/predictive/evaluations/forecast/fc1")).json()
        assert {item["evaluation_type"] for item in evaluations} == {"FORECAST", "DECISION"}
        assert (await client.get("/api/v1/predictive/outcomes/missing")).status_code == 404


@pytest.mark.asyncio
async def test_predictive_analytics_does_not_replace_reactive_api(client_override, db_session) -> None:
    await persist_all(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        predictive = await client.get("/api/v1/predictive/analytics/summary")
        reactive = await client.get("/api/v1/analytics/summary")
        assert predictive.json()["forecast_count"] == 1
        assert reactive.status_code == 200 and "incident_count" in reactive.json()
        assert (await client.get("/")).status_code == 404
