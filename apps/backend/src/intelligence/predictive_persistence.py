"""C19 immutable persistence adapters for validated predictive artifacts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    CapacityProjectionRecord, DriverEvidenceRecord, ForecastDossierRecord,
    ForecastModelArtifactRecord, ForecastRecord, GuardResultRecord,
    InventoryProjectionRecord, PredictiveDecisionRecord, PredictiveFeatureSnapshot,
    RiskCandidateRecord, DecisionTraceRecord,
    ActualOutcomeRecord, PredictiveEvaluationRecord,
)


def contract_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        raw = value.model_dump(mode="json")
    elif is_dataclass(value):
        raw = asdict(value)
    elif isinstance(value, dict):
        raw = value
    else:
        raise TypeError("artifact must be a Pydantic model, dataclass, or dict")
    return json.loads(json.dumps(raw, default=lambda item: item.isoformat() if isinstance(item, datetime) else str(item)))


async def _insert_immutable(db: AsyncSession, model: type, key: Any, row: Any) -> Any:
    existing = await db.get(model, key)
    if existing is None:
        db.add(row); await db.flush(); return row
    if existing.payload != row.payload:
        raise ValueError(f"immutable artifact collision: {key}")
    return existing


async def persist_feature_snapshot(db: AsyncSession, snapshot: Any) -> PredictiveFeatureSnapshot:
    payload = contract_payload(snapshot)
    row = PredictiveFeatureSnapshot(snapshot_id=snapshot.snapshot_id, outlet_id=snapshot.outlet_id,
        sku_id=snapshot.sku_id, service_window=snapshot.service_window,
        prediction_as_of=snapshot.prediction_as_of, window_start=snapshot.window_start,
        window_end=snapshot.window_end, registry_version=snapshot.registry_version,
        fingerprint=snapshot.fingerprint, payload=payload)
    return await _insert_immutable(db, PredictiveFeatureSnapshot, snapshot.snapshot_id, row)


async def persist_forecast(db: AsyncSession, forecast: Any) -> ForecastRecord:
    payload = contract_payload(forecast)
    model_version = getattr(forecast, "model_version", getattr(forecast, "forecast_version", "unknown"))
    row = ForecastRecord(forecast_id=forecast.forecast_id, outlet_id=forecast.outlet_id,
        sku_id=forecast.sku_id, service_window=forecast.service_window,
        prediction_as_of=forecast.prediction_as_of, window_start=forecast.window_start,
        window_end=forecast.window_end, point_demand=forecast.point_demand,
        lower_demand=forecast.lower_demand, upper_demand=forecast.upper_demand,
        model_version=model_version, feature_snapshot_id=forecast.feature_snapshot_id,
        payload=payload)
    return await _insert_immutable(db, ForecastRecord, forecast.forecast_id, row)


async def persist_inventory_projection(db: AsyncSession, projection: Any) -> InventoryProjectionRecord:
    row = InventoryProjectionRecord(projection_id=projection.projection_id,
        forecast_id=projection.forecast_id, outlet_id=projection.outlet_id, sku_id=projection.sku_id,
        shortage_point=projection.shortage_point, stockout_risk=projection.stockout_risk,
        payload=contract_payload(projection))
    return await _insert_immutable(db, InventoryProjectionRecord, projection.projection_id, row)


async def persist_capacity_projection(db: AsyncSession, projection: Any) -> CapacityProjectionRecord:
    row = CapacityProjectionRecord(projection_id=projection.projection_id,
        forecast_id=projection.forecast_id, outlet_id=projection.outlet_id,
        utilization_point=projection.utilization_point, risk_tier=projection.risk_tier.value,
        overloaded=projection.overloaded, payload=contract_payload(projection))
    return await _insert_immutable(db, CapacityProjectionRecord, projection.projection_id, row)


async def persist_driver(db: AsyncSession, driver: Any) -> DriverEvidenceRecord:
    row = DriverEvidenceRecord(driver_id=driver.driver_id, forecast_id=driver.forecast_id,
        feature_id=driver.feature_id, rank=driver.rank, direction=driver.direction.value,
        method=driver.method.value, payload=contract_payload(driver))
    return await _insert_immutable(db, DriverEvidenceRecord, driver.driver_id, row)


async def persist_dossier(db: AsyncSession, dossier: Any) -> ForecastDossierRecord:
    row = ForecastDossierRecord(dossier_id=dossier.dossier_id, outlet_id=dossier.outlet_id,
        service_window=dossier.service_window, window_start=dossier.window_start,
        window_end=dossier.window_end, dossier_version=dossier.dossier_version,
        payload=contract_payload(dossier), created_at=dossier.created_at)
    return await _insert_immutable(db, ForecastDossierRecord, dossier.dossier_id, row)


async def persist_guarded_decision(db: AsyncSession, candidate: Any, guard: Any) -> tuple[PredictiveDecisionRecord, GuardResultRecord]:
    final = guard.final_decision or candidate
    decision = PredictiveDecisionRecord(decision_id=candidate.decision_id,
        dossier_id=candidate.dossier_id, outlet_id=candidate.outlet_id, action=final.action.value,
        status="AWAITING_MANAGER_REVIEW" if guard.disposition.value in {"ACCEPT", "RESTRICT"} else "GUARD_TERMINAL",
        approval_required=final.approval_required, payload=contract_payload(final))
    decision = await _insert_immutable(db, PredictiveDecisionRecord, candidate.decision_id, decision)
    guard_row = GuardResultRecord(guard_result_id=guard.guard_result_id,
        decision_id=candidate.decision_id, disposition=guard.disposition.value,
        valid=guard.valid, payload=contract_payload(guard))
    guard_row = await _insert_immutable(db, GuardResultRecord, guard.guard_result_id, guard_row)
    return decision, guard_row


async def persist_risk_candidate(db: AsyncSession, risk: dict[str, Any]) -> RiskCandidateRecord:
    required = {"risk_id", "outlet_id", "forecast_id", "risk_type", "severity"}
    if not required.issubset(risk): raise ValueError("risk candidate is missing required fields")
    row = RiskCandidateRecord(risk_id=risk["risk_id"], outlet_id=risk["outlet_id"],
        forecast_id=risk["forecast_id"], risk_type=risk["risk_type"], severity=risk["severity"],
        payload=contract_payload(risk))
    return await _insert_immutable(db, RiskCandidateRecord, risk["risk_id"], row)


async def persist_decision_trace(db: AsyncSession, trace: dict[str, Any]) -> DecisionTraceRecord:
    required = {"trace_id", "dossier_id"}
    if not required.issubset(trace): raise ValueError("decision trace is missing required fields")
    row = DecisionTraceRecord(trace_id=trace["trace_id"], dossier_id=trace["dossier_id"],
        decision_id=trace.get("decision_id"), guard_result_id=trace.get("guard_result_id"),
        checkpoint_thread_id=trace.get("checkpoint_thread_id"), payload=contract_payload(trace))
    return await _insert_immutable(db, DecisionTraceRecord, trace["trace_id"], row)


async def persist_actual_outcome(db: AsyncSession, outcome: Any) -> ActualOutcomeRecord:
    row = ActualOutcomeRecord(outcome_id=outcome.outcome_id, forecast_id=outcome.forecast_id,
        outlet_id=outcome.outlet_id, sku_id=outcome.sku_id, service_window=outcome.service_window,
        status=outcome.status.value, matured_at=outcome.matured_at, payload=contract_payload(outcome))
    return await _insert_immutable(db, ActualOutcomeRecord, outcome.outcome_id, row)


async def persist_predictive_evaluation(db: AsyncSession, *, evaluation_type: str,
    forecast_id: str, outcome_id: str, evaluation: Any, decision_id: str | None = None) -> PredictiveEvaluationRecord:
    payload = contract_payload(evaluation)
    encoded = json.dumps({"type": evaluation_type, "forecast": forecast_id, "outcome": outcome_id,
        "decision": decision_id, "payload": payload}, sort_keys=True, separators=(",", ":")).encode()
    from hashlib import sha256
    evaluation_id = f"eval_{sha256(encoded).hexdigest()[:16]}"
    row = PredictiveEvaluationRecord(evaluation_id=evaluation_id, evaluation_type=evaluation_type,
        forecast_id=forecast_id, outcome_id=outcome_id, decision_id=decision_id, payload=payload)
    return await _insert_immutable(db, PredictiveEvaluationRecord, evaluation_id, row)


async def select_forecast_strategy(db: AsyncSession) -> dict[str, Any]:
    artifact = (await db.execute(select(ForecastModelArtifactRecord)
        .where(ForecastModelArtifactRecord.accepted.is_(True))
        .order_by(ForecastModelArtifactRecord.training_cutoff.desc()))).scalars().first()
    if artifact is None:
        return {"strategy": "BASELINE", "artifact_id": None, "reason": "NO_ACCEPTED_ML_ARTIFACT"}
    return {"strategy": "GBT", "artifact_id": artifact.artifact_id,
        "model_version": artifact.model_version, "checksum": artifact.checksum}
