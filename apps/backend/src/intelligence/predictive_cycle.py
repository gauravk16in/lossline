"""C22 end-to-end predictive cycle driven exclusively by canonical events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import tempfile
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lossline_intelligence.attribution import AttributionInput, AttributionMethod, attribute_drivers
from lossline_intelligence.capacity import project_capacity
from lossline_intelligence.decisioning import (
    ActionRisk, DecisionAction, DecisionCandidate, DecisionPolicy, GuardResult,
    RiskType, Urgency,
)
from lossline_intelligence.dossiers import (
    ArtifactRef, CuratedSummary, DataQualitySummary, HistoricalPerformanceSummary,
    build_forecast_dossier,
)
from lossline_intelligence.features.catalog import build_demo_registry
from lossline_intelligence.features.pipeline import (
    SkuFeatureInput, WindowFeatureInput, build_snapshot,
)
from lossline_intelligence.features.snapshot import DatasetRow, FeatureSnapshot
from lossline_intelligence.forecasts.baseline import (
    BaselineAbstention, BaselineForecast, evaluate_rolling_baseline, forecast_baseline,
)
from lossline_intelligence.inventory import project_inventory
from lossline_intelligence.narratives import generate_predictive_explanation
from lossline_intelligence.outcomes import (
    ActualOutcomeStatus, evaluate_decision_outcome, evaluate_forecast_outcome,
    evaluate_risk_predictions, mature_actual_outcome,
)
from lossline_intelligence.retrieval import ComparablePeriod, retrieve_context

from src.db.models import (
    Event, ForecastDossierRecord, ForecastRecord, InventoryProjectionRecord,
    PredictiveDecisionRecord,
)
from src.ingestion.schemas import EventEnvelope
from src.intelligence.predictive_persistence import (
    persist_actual_outcome, persist_capacity_projection, persist_decision_trace,
    persist_dossier, persist_driver, persist_feature_snapshot, persist_forecast,
    persist_guarded_decision, persist_inventory_projection, persist_predictive_evaluation,
    persist_risk_candidate,
)
from src.intelligence.predictive_workflow import SqliteReviewCheckpointStore, run_predictive_workflow

PIPELINE_VERSION = "feature_pipeline.v1"


def _dt(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.tzinfo is None: raise ValueError("predictive event timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _snapshot(*, outlet_id: str, data: dict[str, Any], sku: dict[str, Any],
    prediction_as_of: datetime, source_id: str,
    prior_sku_fulfilled: int | None = None,
    prior_window_end: datetime | None = None) -> FeatureSnapshot:
    context = data["context"]
    promoted = context.get("promoted_sku_id") == sku["sku_id"]
    sku_input = SkuFeatureInput(
        sku_id=sku["sku_id"],
        base_demand=Decimal(str(sku.get("base_demand", sku.get("actual_demand", 0)))),
        workload_minutes=Decimal(str(sku["workload_minutes"])),
        opening_inventory=int(sku["opening_inventory"]),
        promoted=promoted,
        promotion_discount=(
            Decimal(str(context["promotion_discount"]))
            if promoted and context.get("promotion_discount") is not None else None
        ),
        latent_demand=int(sku.get("actual_demand", 0)),
        fulfilled=int(sku.get("fulfilled_quantity", 0)),
        stockout=bool(sku.get("stockout", False)),
    )
    window = WindowFeatureInput(
        outlet_id=outlet_id, service_window=data["service_window"],
        window_start=_dt(data["window_start"]), window_end=_dt(data["window_end"]),
        weekday=int(context["weekday"]),
        weather_state=str(context.get("weather_state", "MISSING")),
        rainfall_mm=(None if context.get("rainfall_mm") is None
            else Decimal(str(context["rainfall_mm"]))),
        is_holiday=bool(context.get("holiday", False)),
        local_event=bool(context.get("local_event", False)),
        delivery_share=Decimal(str(context.get("delivery_share", 0))),
        data_quality=Decimal(str(data["data_quality"])),
        available_capacity_minutes=Decimal(str(data["available_capacity_minutes"])),
        sku_inputs=(sku_input,),
    )
    snapshot = build_snapshot(window, sku_input, registry=build_demo_registry(),
        prediction_as_of=prediction_as_of, prior_sku_fulfilled=prior_sku_fulfilled,
        prior_window_end=prior_window_end)
    return snapshot.model_copy(update={"source_signal_ids": (source_id,),
        "created_at": prediction_as_of})


async def _history_rows(db: AsyncSession, *, outlet_id: str, prediction_as_of: datetime) -> tuple[DatasetRow, ...]:
    events = (await db.execute(select(Event).where(Event.restaurant_id == outlet_id,
        Event.event_type == "demand.window_observed").order_by(Event.occurred_at))).scalars().all()
    rows: list[DatasetRow] = []
    prior_by_sku: dict[str, tuple[int, datetime]] = {}
    for event in events:
        data = event.data
        if _dt(data["window_end"]) >= prediction_as_of: continue
        for sku in data["skus"]:
            prior = prior_by_sku.get(sku["sku_id"])
            snap = _snapshot(outlet_id=outlet_id, data=data, sku=sku,
                prediction_as_of=_dt(data["window_start"]) - timedelta(hours=1),
                source_id=event.event_id,
                prior_sku_fulfilled=None if prior is None else prior[0],
                prior_window_end=None if prior is None else prior[1])
            rows.append(DatasetRow(snap, int(sku["actual_demand"]), int(sku["fulfilled_quantity"]), bool(sku["stockout"])))
            prior_by_sku[sku["sku_id"]] = (int(sku["fulfilled_quantity"]), _dt(data["window_end"]))
    return tuple(rows)


class _DeterministicProvider:
    model_name = "deterministic-playbook.v1"
    def __init__(self, candidate: DecisionCandidate): self.candidate = candidate
    def propose(self, **_: Any) -> dict[str, Any]:
        return {"tool_name": "submit_operational_decision", "arguments": self.candidate.model_dump(mode="json")}


async def process_scheduled_window(db: AsyncSession, envelope: EventEnvelope) -> dict[str, Any]:
    data = envelope.data; prediction_as_of = envelope.occurred_at
    history = await _history_rows(db, outlet_id=envelope.restaurant_id, prediction_as_of=prediction_as_of)
    forecasts: list[BaselineForecast] = []; inventories = []; drivers = []
    for sku in data["skus"]:
        prior_rows = [row for row in history if row.snapshot.sku_id == sku["sku_id"]]
        prior = max(prior_rows, key=lambda row: row.snapshot.window_end) if prior_rows else None
        snapshot = _snapshot(outlet_id=envelope.restaurant_id, data=data, sku=sku,
            prediction_as_of=prediction_as_of, source_id=envelope.event_id,
            prior_sku_fulfilled=None if prior is None else prior.observed_demand_quantity,
            prior_window_end=None if prior is None else prior.snapshot.window_end)
        await persist_feature_snapshot(db, snapshot)
        result = forecast_baseline(snapshot, history, prediction_as_of=prediction_as_of, min_history=4)
        if isinstance(result, BaselineAbstention):
            raise ValueError(f"predictive cycle abstained: {result.reason.value}")
        forecasts.append(result); await persist_forecast(db, result)
        inventory = project_inventory(result, opening_inventory=int(sku["opening_inventory"]),
            replenishment_quantity=int(sku.get("replenishment_quantity", 0)), evidence_ids=(snapshot.snapshot_id,))
        inventories.append(inventory); await persist_inventory_projection(db, inventory)
        promoted = data["context"].get("promoted_sku_id") == sku["sku_id"]
        feature_id = "promotion.discount_pct" if promoted else "sku.base_demand"
        score = Decimal(str(data["context"].get("promotion_discount") or 0)) if promoted else Decimal("0")
        driver = attribute_drivers(forecast_id=result.forecast_id,
            registered_feature_ids=(feature_id,), candidates=(AttributionInput(feature_id,
                snapshot.snapshot_id, score, AttributionMethod.DETERMINISTIC_DEVIATION),))[0]
        drivers.append(driver); await persist_driver(db, driver)

    capacity = project_capacity(forecast_id="group_" + sha256("|".join(f.forecast_id for f in forecasts).encode()).hexdigest()[:16],
        outlet_id=envelope.restaurant_id, service_window=data["service_window"],
        window_start=_dt(data["window_start"]), window_end=_dt(data["window_end"]),
        sku_workloads=tuple((f.point_demand, f.lower_demand, f.upper_demand,
            Decimal(str(sku["workload_minutes"]))) for f, sku in zip(forecasts, data["skus"])),
        available_capacity_minutes=Decimal(str(data["available_capacity_minutes"])),
        evidence_ids=tuple(f.forecast_id for f in forecasts))
    await persist_capacity_projection(db, capacity)

    risk_refs: list[ArtifactRef] = []
    for forecast, inventory in zip(forecasts, inventories):
        if inventory.stockout_risk:
            risk_id = f"risk_{inventory.projection_id}"
            await persist_risk_candidate(db, {"risk_id": risk_id, "outlet_id": envelope.restaurant_id,
                "forecast_id": forecast.forecast_id, "risk_type": "INVENTORY_SHORTAGE",
                "severity": inventory.shortage_severity.value, "evidence_ids": [inventory.projection_id]})
            risk_refs.append(ArtifactRef(artifact_id=risk_id, artifact_type="risk", version="v1"))
    if capacity.overloaded:
        risk_id = f"risk_{capacity.projection_id}"
        await persist_risk_candidate(db, {"risk_id": risk_id, "outlet_id": envelope.restaurant_id,
            "forecast_id": forecasts[0].forecast_id, "risk_type": "CAPACITY_OVERLOAD",
            "severity": capacity.risk_tier.value, "evidence_ids": [capacity.projection_id]})
        risk_refs.append(ArtifactRef(artifact_id=risk_id, artifact_type="risk", version="v1"))

    history_events = (await db.execute(select(Event).where(
        Event.restaurant_id == envelope.restaurant_id,
        Event.event_type == "demand.window_observed",
        Event.occurred_at < prediction_as_of).order_by(Event.occurred_at))).scalars().all()
    comparable_periods = tuple(ComparablePeriod(
        period_id=f"period_{event.event_id}", outlet_id=envelope.restaurant_id,
        service_window=event.data["service_window"],
        window_start=_dt(event.data["window_start"]), sku_id=None, risk_type=None,
        summary=(f"Observed {sum(int(item['actual_demand']) for item in event.data['skus'])} "
            f"orders in the {event.data['service_window']} window."),
        evidence_ids=(event.event_id,),
    ) for event in history_events)
    retrieval = retrieve_context(outlet_id=envelope.restaurant_id,
        service_window=data["service_window"], prediction_as_of=prediction_as_of,
        comparable_periods=comparable_periods)
    similar_periods = tuple(CuratedSummary(summary_id=item.item_id,
        summary_type=item.source_type, text=item.summary,
        evidence_ids=item.evidence_ids) for item in retrieval.structured)
    baseline_metrics = evaluate_rolling_baseline(history, min_history=4)
    historical_performance = (() if baseline_metrics.mae is None else (
        HistoricalPerformanceSummary(evaluation_id="history_baseline_rolling",
            sample_count=baseline_metrics.forecast_count,
            mae=baseline_metrics.mae, wmape=baseline_metrics.wmape),
    ))

    dossier = build_forecast_dossier(outlet_id=envelope.restaurant_id,
        service_window=data["service_window"], window_start=_dt(data["window_start"]),
        window_end=_dt(data["window_end"]), prediction_as_of=prediction_as_of,
        forecast_refs=tuple(ArtifactRef(artifact_id=f.forecast_id, artifact_type="forecast", version=f.forecast_version) for f in forecasts),
        feature_snapshot_refs=tuple(ArtifactRef(artifact_id=f.feature_snapshot_id, artifact_type="snapshot", version=PIPELINE_VERSION) for f in forecasts),
        inventory_refs=tuple(ArtifactRef(artifact_id=i.projection_id, artifact_type="inventory", version=i.rule_version) for i in inventories),
        capacity_refs=(ArtifactRef(artifact_id=capacity.projection_id, artifact_type="capacity", version=capacity.rule_version),),
        risk_refs=tuple(risk_refs), driver_refs=tuple(ArtifactRef(artifact_id=d.driver_id,
            artifact_type="driver", version=d.rule_version) for d in drivers),
        historical_performance=historical_performance,
        similar_periods=similar_periods,
        data_quality=DataQualitySummary(tier="HIGH" if Decimal(str(data["data_quality"])) >= Decimal("0.8") else "LOW"),
        provenance_ids=(envelope.event_id,), created_at=prediction_as_of)
    await persist_dossier(db, dossier)

    shortage_index = next((index for index, item in enumerate(inventories) if item.stockout_risk), None)
    if shortage_index is not None:
        chosen_f, chosen_i, chosen_d = forecasts[shortage_index], inventories[shortage_index], drivers[shortage_index]
        action, risk_type, quantity, unit, sku_id = (DecisionAction.ADJUST_PREP_QUANTITY,
            RiskType.INVENTORY_SHORTAGE, Decimal(chosen_i.shortage_point), "portions", chosen_f.sku_id)
        forecast_id, evidence_ids, reason = chosen_f.forecast_id, (chosen_d.driver_id, chosen_i.projection_id), "PROJECTED_SHORTAGE"
    elif capacity.overloaded:
        action, risk_type, quantity, unit, sku_id = DecisionAction.REALLOCATE_STAFF, RiskType.CAPACITY_OVERLOAD, None, None, None
        forecast_id, evidence_ids, reason = forecasts[0].forecast_id, (capacity.projection_id,), "PROJECTED_OVERLOAD"
    else:
        action, risk_type, quantity, unit, sku_id = DecisionAction.NO_ACTION, RiskType.NONE, None, None, None
        forecast_id, evidence_ids, reason = forecasts[0].forecast_id, (forecasts[0].forecast_id,), "NO_PROJECTED_RISK"
    decision_id = "dec_" + sha256((dossier.dossier_id + action.value).encode()).hexdigest()[:16]
    candidate = DecisionCandidate(decision_id=decision_id, decision_version="v1",
        dossier_id=dossier.dossier_id, forecast_id=forecast_id, outlet_id=envelope.restaurant_id,
        service_window=data["service_window"], window_start=_dt(data["window_start"]),
        window_end=_dt(data["window_end"]), risk_type=risk_type, sku_id=sku_id,
        action=action, quantity=quantity, unit=unit, execute_by=_dt(data["window_start"]),
        reason_code=reason, evidence_ids=evidence_ids, urgency=Urgency.HIGH if risk_type is not RiskType.NONE else Urgency.LOW,
        action_risk=ActionRisk.MEDIUM if action is not DecisionAction.NO_ACTION else ActionRisk.LOW,
        approval_required=action is not DecisionAction.NO_ACTION)
    checkpoint = SqliteReviewCheckpointStore(Path(tempfile.gettempdir()) / "lossline-predictive-checkpoints.sqlite")
    state = run_predictive_workflow(thread_id=dossier.dossier_id, dossier=dossier,
        provider=_DeterministicProvider(candidate), policy=DecisionPolicy(policy_id="demo-policy.v1",
            allowed_actions=(DecisionAction.NO_ACTION, DecisionAction.ABSTAIN,
                DecisionAction.ADJUST_PREP_QUANTITY, DecisionAction.REALLOCATE_STAFF),
            max_prep_quantity=Decimal("25")), checkpoint_store=checkpoint)
    if state["guard_result"] is None: raise ValueError("predictive workflow produced no guard result")
    guard = GuardResult.model_validate(state["guard_result"])
    await persist_guarded_decision(db, candidate, guard)
    explanation = generate_predictive_explanation(dossier=dossier, guard_result=guard)
    trace_id = "trace_" + sha256(dossier.dossier_id.encode()).hexdigest()[:16]
    await persist_decision_trace(db, {"trace_id": trace_id, "dossier_id": dossier.dossier_id,
        "decision_id": candidate.decision_id, "guard_result_id": guard.guard_result_id,
        "checkpoint_thread_id": dossier.dossier_id, "explanation": explanation.result.model_dump(mode="json"),
        "explanation_source": explanation.source, "stages": state["stages"]})
    return {"dossier_id": dossier.dossier_id, "decision_id": candidate.decision_id,
        "forecast_ids": [item.forecast_id for item in forecasts], "trace_id": trace_id}


async def process_observed_window(db: AsyncSession, envelope: EventEnvelope) -> tuple[str, ...]:
    data = envelope.data; start, end = _dt(data["window_start"]), _dt(data["window_end"])
    records = (await db.execute(select(ForecastRecord).where(
        ForecastRecord.outlet_id == envelope.restaurant_id,
        ForecastRecord.service_window == data["service_window"]))).scalars().all()
    records = [record for record in records if _dt(record.payload["window_start"]) == start and _dt(record.payload["window_end"]) == end]
    persisted: list[str] = []
    for record in records:
        sku = next((item for item in data["skus"] if item["sku_id"] == record.sku_id), None)
        if sku is None: continue
        forecast = BaselineForecast.model_validate(record.payload)
        outcome = mature_actual_outcome(forecast=forecast, now=envelope.occurred_at,
            actual_demand=Decimal(sku["actual_demand"]), fulfilled_quantity=Decimal(sku["fulfilled_quantity"]),
            unfulfilled_quantity=Decimal(sku["unfulfilled_quantity"]), ending_inventory=Decimal(sku["ending_inventory"]),
            capacity_utilization=Decimal(str(data["capacity_utilization"])),
            status=ActualOutcomeStatus.AVAILABLE, source_ids=(envelope.event_id,))
        if not hasattr(outcome, "outcome_id"): continue
        await persist_actual_outcome(db, outcome); persisted.append(outcome.outcome_id)
        forecast_eval = evaluate_forecast_outcome(forecast, outcome)
        if forecast_eval is not None:
            await persist_predictive_evaluation(db, evaluation_type="FORECAST",
                forecast_id=forecast.forecast_id, outcome_id=outcome.outcome_id, evaluation=forecast_eval)
        projection = (await db.execute(select(InventoryProjectionRecord).where(
            InventoryProjectionRecord.forecast_id == forecast.forecast_id))).scalars().first()
        if projection is not None:
            risk_eval = evaluate_risk_predictions(((bool(projection.stockout_risk), int(sku["unfulfilled_quantity"]) > 0),))
            await persist_predictive_evaluation(db, evaluation_type="RISK", forecast_id=forecast.forecast_id,
                outcome_id=outcome.outcome_id, evaluation=risk_eval)
        dossiers = (await db.execute(select(ForecastDossierRecord).where(
            ForecastDossierRecord.outlet_id == envelope.restaurant_id))).scalars().all()
        dossier_ids = [row.dossier_id for row in dossiers if any(ref["artifact_id"] == forecast.forecast_id for ref in row.payload["forecast_refs"])]
        if dossier_ids:
            decision = (await db.execute(select(PredictiveDecisionRecord).where(
                PredictiveDecisionRecord.dossier_id.in_(dossier_ids),
                PredictiveDecisionRecord.manager_decision.is_not(None)))).scalars().first()
            if decision is not None:
                decision_eval = evaluate_decision_outcome(decision_id=decision.decision_id,
                    manager_decision=decision.manager_decision, outcome=outcome)
                await persist_predictive_evaluation(db, evaluation_type="DECISION",
                    forecast_id=forecast.forecast_id, outcome_id=outcome.outcome_id,
                    decision_id=decision.decision_id, evaluation=decision_eval)
    return tuple(persisted)
