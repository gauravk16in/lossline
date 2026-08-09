import asyncio
import datetime
import hashlib
import json
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict

from src.db.session import get_db_session
from src.db.models import (
    Restaurant,
    Event,
    Incident,
    Recommendation,
    Action,
    Outcome,
    ScenarioRun,
    incident_signals,
    Signal,
    ForecastRecord,
    InventoryProjectionRecord,
    CapacityProjectionRecord,
    ForecastDossierRecord,
    PredictiveDecisionRecord,
    RiskCandidateRecord,
    DecisionTraceRecord,
    GuardResultRecord,
    DriverEvidenceRecord,
    PredictiveFeatureSnapshot,
    ForecastModelArtifactRecord,
    ActualOutcomeRecord,
    PredictiveEvaluationRecord,
)
from src.ingestion.schemas import EventEnvelope, EventType
from src.realtime.websocket import manager
from src.config import settings
from src.demo.entities import DEMO_RESTAURANTS
from src.intelligence.outcomes import verify_incident_outcome
from src.intelligence.predictive_persistence import select_forecast_strategy
from src.api.security import (
    IngestionContext, UserContext, require_admin_key, require_ingest_key,
    require_manager_key, require_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def organization_filter(user: UserContext):
    """Local demo remains unscoped; production always resolves a real organization."""
    return True if not settings.SERVERLESS_MODE else Restaurant.organization_id == user.organization_id


async def require_owned_outlet(db: AsyncSession, user: UserContext, outlet_id: str) -> Restaurant:
    stmt = select(Restaurant).where(Restaurant.id == outlet_id)
    if settings.SERVERLESS_MODE: stmt = stmt.where(Restaurant.organization_id == user.organization_id)
    row = (await db.execute(stmt)).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Outlet not found")
    return row


def compute_payload_hash(envelope: EventEnvelope) -> str:
    """
    Computes a stable deterministic SHA256 hash of the event envelope.
    """
    serialized = json.dumps(envelope.model_dump(), sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@router.post("/events", status_code=202)
async def ingest_event(
    envelope: EventEnvelope, db: AsyncSession = Depends(get_db_session),
    ingestion: IngestionContext = Depends(require_ingest_key),
):
    """
    Ingests canonical events, checking for duplicates and auto-provisioning restaurants.
    """
    p_hash = compute_payload_hash(envelope)

    # Check for duplicate event_id
    result = await db.execute(select(Event).filter(Event.event_id == envelope.event_id))
    existing_event = result.scalars().first()

    if existing_event:
        if existing_event.payload_hash == p_hash:
            logger.info(
                f"Duplicate event {envelope.event_id} received with identical payload. Returning 202."
            )
            if existing_event.processing_status == "COMPLETED":
                return {
                "event_id": envelope.event_id,
                "status": "accepted",
                "duplicate": True,
                "processing_status": "COMPLETED",
                **(existing_event.processing_result or {}),
                }
            if existing_event.processing_status == "PROCESSING":
                return {"event_id": envelope.event_id, "status": "accepted", "duplicate": True,
                    "processing_status": "PROCESSING"}
        else:
            logger.warning(
                f"Conflict: Event {envelope.event_id} received with differing payload."
            )
            raise HTTPException(
                status_code=409,
                detail=f"Event ID {envelope.event_id} already exists with a different payload.",
            )

    if settings.SERVERLESS_MODE and envelope.metadata.synthetic:
        raise HTTPException(status_code=422, detail="Synthetic events are prohibited in production")
    if settings.SERVERLESS_MODE and envelope.outlet_id not in ingestion.allowed_outlet_ids:
        raise HTTPException(status_code=403, detail="Integration is not authorized for this outlet")

    # Auto-provisioning is strictly a local demo convenience.
    res_check = await db.execute(
        select(Restaurant).filter(Restaurant.id == envelope.restaurant_id)
    )
    restaurant = res_check.scalars().first()
    if not restaurant and settings.SERVERLESS_MODE:
        raise HTTPException(status_code=404, detail="Outlet must be provisioned before ingestion")
    if restaurant and settings.SERVERLESS_MODE and restaurant.organization_id != ingestion.organization_id:
        raise HTTPException(status_code=403, detail="Integration is not authorized for this outlet")
    if not restaurant:
        logger.info(f"Auto-provisioning missing restaurant: {envelope.restaurant_id}")
        demo_restaurant = DEMO_RESTAURANTS.get(envelope.restaurant_id)
        restaurant = Restaurant(
            id=envelope.restaurant_id,
            name=(
                demo_restaurant.name
                if demo_restaurant
                else f"Outlet {envelope.restaurant_id}"
            ),
            timezone=demo_restaurant.timezone if demo_restaurant else "UTC",
            currency=demo_restaurant.currency if demo_restaurant else "INR",
            synthetic=True,
            metadata_json=(dict(demo_restaurant.metadata) if demo_restaurant else None),
        )
        db.add(restaurant)
        await db.flush()  # Flush so FK is resolvable

    # Write event record to outbox (published_to_stream = False)
    new_event = existing_event or Event(
        event_id=envelope.event_id,
        restaurant_id=envelope.restaurant_id,
        outlet_id=envelope.outlet_id,
        scenario_run_id=envelope.metadata.scenario_run_id,
        source=envelope.source.value,
        event_type=envelope.event_type.value,
        occurred_at=envelope.occurred_at,
        entity=envelope.entity.model_dump(),
        data=envelope.data,
        metadata_json=envelope.metadata.model_dump(),
        schema_version=envelope.schema_version,
        payload_hash=p_hash,
        published_to_stream=settings.SERVERLESS_MODE,
        processing_status="PENDING",
    )
    if existing_event is None: db.add(new_event)
    new_event.processing_status = "PROCESSING"
    new_event.processing_attempt_count += 1
    new_event.processing_last_error = None
    await db.flush()

    try:
        predictive_result = None
        if envelope.event_type == EventType.PREDICTIVE_WINDOW_SCHEDULED:
            from src.intelligence.predictive_cycle import process_scheduled_window
            predictive_result = await process_scheduled_window(db, envelope)
        elif envelope.event_type == EventType.DEMAND_WINDOW_OBSERVED:
            from src.intelligence.predictive_cycle import process_observed_window
            predictive_result = {"outcome_ids": list(await process_observed_window(db, envelope))}
        elif settings.INLINE_PROCESSING:
            await db.commit()
            from src.intelligence.pipeline import run_detection_pipeline
            await run_detection_pipeline(envelope, db_session=db)
        incident_ids = list((await db.execute(select(Incident.id).where(
            Incident.restaurant_id == envelope.outlet_id,
            Incident.window_start <= envelope.occurred_at,
            Incident.window_end >= envelope.occurred_at))).scalars().all())
        result_payload = {"predictive": predictive_result, "incident_ids": incident_ids,
            "artifact_ids": list((predictive_result or {}).values()) if predictive_result else []}
        new_event.processing_status = "COMPLETED"
        new_event.processing_result = result_payload
        await db.flush()
    except Exception as exc:
        await db.rollback()
        failed = (await db.execute(select(Event).where(Event.event_id == envelope.event_id))).scalars().first()
        if failed is not None:
            failed.processing_status = "FAILED"; failed.processing_last_error = str(exc)[:2000]
            failed.processing_attempt_count = max(failed.processing_attempt_count, new_event.processing_attempt_count)
            await db.commit()
        logger.exception("Synchronous processing failed for event %s", envelope.event_id)
        raise HTTPException(status_code=500, detail="Event persisted but intelligence processing failed") from exc

    return {"event_id": envelope.event_id, "status": "accepted", "duplicate": existing_event is not None,
        "processing_status": new_event.processing_status, **result_payload}


@router.get("/restaurants")
async def get_restaurants(db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    """
    Get all active restaurants and basic details.
    """
    result = await db.execute(select(Restaurant).where(organization_filter(user)))
    return result.scalars().all()


@router.get("/incidents")
async def get_incidents(
    status: str | None = None, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)
):
    """
    Retrieves the incident feed.
    """
    stmt = select(Incident).join(Restaurant).where(organization_filter(user))
    if status:
        stmt = stmt.filter(Incident.status == status)
    stmt = stmt.options(selectinload(Incident.recommendations)).order_by(
        Incident.created_at.desc()
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/incidents/{id}")
async def get_incident(id: int, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    """
    Retrieves full details of a specific incident, including associated signals and recommendations.
    """
    stmt = (
        select(Incident)
        .join(Restaurant).filter(Incident.id == id).where(organization_filter(user))
        .options(selectinload(Incident.signals), selectinload(Incident.recommendations))
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        column.name: getattr(incident, column.name) for column in Incident.__table__.columns
    } | {
        "signals": [
            {column.name: getattr(signal, column.name) for column in Signal.__table__.columns}
            for signal in incident.signals
        ],
        "recommendations": [
            {column.name: getattr(rec, column.name) for column in Recommendation.__table__.columns}
            for rec in incident.recommendations
        ],
    }


class DecisionPayload(BaseModel):
    decision: Literal["APPROVE", "REJECT", "EDIT"]
    final_action_text: str | None = None
    manager_note: str | None = None
    idempotency_key: str


class ScenarioRunPayload(BaseModel):
    scenario_id: str = "meghana_lunch_rush_v1"
    seed: int = 42
    speed: float = 120.0


class PredictiveManagerReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVE", "REJECT"]
    idempotency_key: str
    manager_note: str | None = None


@router.get("/predictive/forecasts/{outlet_id}/{service_window}")
async def get_predictive_forecasts(outlet_id: str, service_window: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    await require_owned_outlet(db, user, outlet_id)
    rows = (await db.execute(select(ForecastRecord).where(
        ForecastRecord.outlet_id == outlet_id,
        ForecastRecord.service_window == service_window,
    ).order_by(ForecastRecord.window_start.desc(), ForecastRecord.sku_id))).scalars().all()
    return [row.payload for row in rows]


@router.get("/predictive/service-windows/{outlet_id}")
async def get_predictive_service_windows(outlet_id: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    await require_owned_outlet(db, user, outlet_id)
    """Return user-selectable service windows backed by persisted forecasts."""
    rows = (await db.execute(select(ForecastRecord.service_window).where(
        ForecastRecord.outlet_id == outlet_id).distinct())).scalars().all()
    # Hourly records are chart detail, not a separate meal period selector.
    windows = sorted({value.removesuffix("_HOURLY") for value in rows
        if value not in {"HOURLY"}})
    return {"outlet_id": outlet_id, "service_windows": windows}


@router.get("/predictive/today/{outlet_id}/{service_window}")
async def get_predictive_today(outlet_id: str, service_window: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    outlet = await require_owned_outlet(db, user, outlet_id)
    forecasts = (await db.execute(select(ForecastRecord).where(
        ForecastRecord.outlet_id == outlet_id,
        ForecastRecord.service_window == service_window,
    ).order_by(ForecastRecord.window_start, ForecastRecord.sku_id))).scalars().all()
    forecast_ids = [row.forecast_id for row in forecasts]
    snapshot_ids = [row.feature_snapshot_id for row in forecasts]
    snapshots = [] if not snapshot_ids else (await db.execute(select(
        PredictiveFeatureSnapshot).where(
        PredictiveFeatureSnapshot.snapshot_id.in_(snapshot_ids)))).scalars().all()
    inventories = [] if not forecast_ids else (await db.execute(select(InventoryProjectionRecord).where(
        InventoryProjectionRecord.forecast_id.in_(forecast_ids)))).scalars().all()
    capacity_rows = (await db.execute(select(CapacityProjectionRecord).where(
        CapacityProjectionRecord.outlet_id == outlet_id))).scalars().all()
    capacities = [row for row in capacity_rows
        if row.payload.get("service_window") == service_window]
    risks = [] if not forecast_ids else (await db.execute(select(RiskCandidateRecord).where(
        RiskCandidateRecord.forecast_id.in_(forecast_ids)))).scalars().all()
    drivers = [] if not forecast_ids else (await db.execute(select(DriverEvidenceRecord).where(
        DriverEvidenceRecord.forecast_id.in_(forecast_ids)).order_by(DriverEvidenceRecord.rank))).scalars().all()
    dossiers = (await db.execute(select(ForecastDossierRecord).where(
        ForecastDossierRecord.outlet_id == outlet_id,
        ForecastDossierRecord.service_window == service_window).order_by(
        ForecastDossierRecord.created_at.desc()))).scalars().all()
    dossier_ids = [row.dossier_id for row in dossiers]
    decisions = [] if not dossier_ids else (await db.execute(select(PredictiveDecisionRecord).where(
        PredictiveDecisionRecord.dossier_id.in_(dossier_ids)))).scalars().all()
    outcomes = [] if not forecast_ids else (await db.execute(select(ActualOutcomeRecord).where(
        ActualOutcomeRecord.forecast_id.in_(forecast_ids)))).scalars().all()
    evaluations = [] if not forecast_ids else (await db.execute(select(
        PredictiveEvaluationRecord).where(
        PredictiveEvaluationRecord.forecast_id.in_(forecast_ids)).order_by(
        PredictiveEvaluationRecord.created_at))).scalars().all()
    return {"outlet_id": outlet_id, "service_window": service_window,
        "forecasts": [row.payload for row in forecasts],
        "feature_snapshots": [row.payload for row in snapshots],
        "inventory_projections": [row.payload for row in inventories],
        "capacity_projections": [row.payload for row in capacities],
        "risks": [row.payload for row in risks], "drivers": [row.payload for row in drivers],
        "dossiers": [row.payload for row in dossiers],
        "decisions": [{"decision": row.payload, "status": row.status,
            "manager_decision": row.manager_decision} for row in decisions],
        "outcomes": [row.payload for row in outcomes],
        "evaluations": [{"evaluation_id": row.evaluation_id,
            "evaluation_type": row.evaluation_type, "forecast_id": row.forecast_id,
            "decision_id": row.decision_id, "evaluation": row.payload}
            for row in evaluations],
        "synthetic": outlet.synthetic}


@router.get("/predictive/features/{snapshot_id}")
async def get_predictive_feature_snapshot(snapshot_id: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(PredictiveFeatureSnapshot).join(Restaurant,
        PredictiveFeatureSnapshot.outlet_id == Restaurant.id).where(
        PredictiveFeatureSnapshot.snapshot_id == snapshot_id, organization_filter(user)))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Feature snapshot not found")
    return row.payload


@router.get("/predictive/projections/inventory/{projection_id}")
async def get_predictive_inventory_projection(projection_id: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(InventoryProjectionRecord).join(Restaurant,
        InventoryProjectionRecord.outlet_id == Restaurant.id).where(
        InventoryProjectionRecord.projection_id == projection_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Inventory projection not found")
    return row.payload


@router.get("/predictive/projections/capacity/{projection_id}")
async def get_predictive_capacity_projection(projection_id: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(CapacityProjectionRecord).join(Restaurant,
        CapacityProjectionRecord.outlet_id == Restaurant.id).where(
        CapacityProjectionRecord.projection_id == projection_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Capacity projection not found")
    return row.payload


@router.get("/predictive/dossiers/{dossier_id}")
async def get_predictive_dossier(dossier_id: str, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(ForecastDossierRecord).join(Restaurant,
        ForecastDossierRecord.outlet_id == Restaurant.id).where(
        ForecastDossierRecord.dossier_id == dossier_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Forecast dossier not found")
    return row.payload


@router.get("/predictive/decisions/{decision_id}")
async def get_predictive_decision(decision_id: str, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(PredictiveDecisionRecord).join(Restaurant,
        PredictiveDecisionRecord.outlet_id == Restaurant.id).where(
        PredictiveDecisionRecord.decision_id == decision_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Predictive decision not found")
    return {"decision": row.payload, "status": row.status, "manager_decision": row.manager_decision,
        "manager_id": row.manager_id, "manager_note": row.manager_note}


@router.post("/predictive/decisions/{decision_id}/review")
async def review_predictive_decision(decision_id: str, payload: PredictiveManagerReviewPayload,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_manager_key)):
    if not payload.idempotency_key.strip():
        raise HTTPException(status_code=422, detail="idempotency_key must be non-empty")
    replay = (await db.execute(select(PredictiveDecisionRecord).where(
        PredictiveDecisionRecord.idempotency_key == payload.idempotency_key))).scalars().first()
    if replay is not None:
        if replay.decision_id != decision_id or replay.manager_decision != payload.decision:
            raise HTTPException(status_code=409, detail="Idempotency key already used for a different review")
        return {"decision_id": replay.decision_id, "status": replay.status, "duplicate": True}
    row = (await db.execute(select(PredictiveDecisionRecord).join(Restaurant,
        PredictiveDecisionRecord.outlet_id == Restaurant.id).where(
        PredictiveDecisionRecord.decision_id == decision_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Predictive decision not found")
    if row.status != "AWAITING_MANAGER_REVIEW":
        raise HTTPException(status_code=409, detail="Decision is not awaiting manager review")
    trace = (await db.execute(select(DecisionTraceRecord).where(
        DecisionTraceRecord.decision_id == decision_id))).scalars().first()
    if trace is not None and trace.checkpoint_thread_id:
        from pathlib import Path
        import tempfile
        from src.intelligence.predictive_workflow import (
            SqliteReviewCheckpointStore, resume_manager_review,
        )
        try:
            resume_manager_review(thread_id=trace.checkpoint_thread_id,
                manager_decision=payload.decision,
                checkpoint_store=SqliteReviewCheckpointStore(
                    Path(tempfile.gettempdir()) / "lossline-predictive-checkpoints.sqlite"))
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=f"Predictive checkpoint conflict: {exc}")
    row.manager_decision = payload.decision
    row.manager_id = user.subject
    row.manager_note = payload.manager_note
    row.idempotency_key = payload.idempotency_key.strip()
    row.decided_at = datetime.datetime.now(datetime.timezone.utc)
    row.status = "MANAGER_APPROVED" if payload.decision == "APPROVE" else "MANAGER_REJECTED"
    await db.flush()
    await manager.broadcast_transition({"message_id": f"msg_pred_{row.decision_id}",
        "decision_id": row.decision_id, "dossier_id": row.dossier_id, "stage": row.status,
        "status": "success", "occurred_at": row.decided_at.isoformat()})
    return {"decision_id": row.decision_id, "status": row.status, "duplicate": False}


@router.get("/predictive/model-strategy")
async def predictive_model_strategy(db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    return await select_forecast_strategy(db)


@router.get("/predictive/outcomes/{forecast_id}")
async def get_predictive_outcome(forecast_id: str, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    row = (await db.execute(select(ActualOutcomeRecord).join(Restaurant,
        ActualOutcomeRecord.outlet_id == Restaurant.id).where(
        ActualOutcomeRecord.forecast_id == forecast_id, organization_filter(user)))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Matured outcome not found")
    return row.payload


@router.get("/predictive/evaluations/forecast/{forecast_id}")
async def get_predictive_forecast_evaluations(forecast_id: str,
    db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    owned = (await db.execute(select(ForecastRecord.forecast_id).join(Restaurant,
        ForecastRecord.outlet_id == Restaurant.id).where(ForecastRecord.forecast_id == forecast_id,
        organization_filter(user)))).scalar_one_or_none()
    if owned is None: raise HTTPException(status_code=404, detail="Forecast not found")
    rows = (await db.execute(select(PredictiveEvaluationRecord).where(
        PredictiveEvaluationRecord.forecast_id == forecast_id).order_by(
        PredictiveEvaluationRecord.created_at))).scalars().all()
    return [{"evaluation_id": row.evaluation_id, "evaluation_type": row.evaluation_type,
        "decision_id": row.decision_id, "evaluation": row.payload} for row in rows]


@router.get("/predictive/analytics/summary")
async def predictive_analytics_summary(db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    outlet_ids = select(Restaurant.id).where(organization_filter(user))
    return {
        "forecast_count": await db.scalar(select(func.count(ForecastRecord.forecast_id)).where(ForecastRecord.outlet_id.in_(outlet_ids))) or 0,
        "risk_count": await db.scalar(select(func.count(RiskCandidateRecord.risk_id)).where(RiskCandidateRecord.outlet_id.in_(outlet_ids))) or 0,
        "pending_review_count": await db.scalar(select(func.count(PredictiveDecisionRecord.decision_id)).where(
            PredictiveDecisionRecord.status == "AWAITING_MANAGER_REVIEW", PredictiveDecisionRecord.outlet_id.in_(outlet_ids))) or 0,
        "synthetic": False if settings.SERVERLESS_MODE else True,
    }


@router.post("/demo/runs", status_code=201)
async def create_demo_run(
    payload: ScenarioRunPayload, db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_key),
):
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo runs are disabled")
    run = ScenarioRun(
        scenario_id=payload.scenario_id,
        seed=payload.seed,
        speed=payload.speed,
        status="RUNNING",
    )
    db.add(run)
    await db.flush()
    return run


@router.post("/demo/runs/{id}/complete")
async def complete_demo_run(id: int, db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_key)):
    run = (
        (await db.execute(select(ScenarioRun).where(ScenarioRun.id == id)))
        .scalars()
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    run.status = "COMPLETED"
    run.completed_at = datetime.datetime.now(datetime.timezone.utc)
    return run


@router.delete("/demo/runs/{run_id}")
async def delete_demo_run(run_id: str, db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_key)):
    """Delete only synthetic artifacts attributable to one scenario run."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo runs are disabled")
    run = await db.get(ScenarioRun, int(run_id)) if run_id.isdigit() else None
    if run is None:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    event_rows = (await db.execute(select(Event).where(
        Event.scenario_run_id == run_id,
    ))).scalars().all()
    event_ids = {row.event_id for row in event_rows}
    signal_rows = (await db.execute(select(Signal))).scalars().all()
    signal_ids = {row.id for row in signal_rows if event_ids.intersection(row.evidence_event_ids)}
    incident_ids = set()
    if signal_ids:
        incident_ids = set((await db.execute(select(incident_signals.c.incident_id).where(
            incident_signals.c.signal_id.in_(signal_ids)))).scalars().all())
    if incident_ids:
        await db.execute(delete(Outcome).where(Outcome.incident_id.in_(incident_ids)))
        recommendation_ids = set((await db.execute(select(Recommendation.id).where(
            Recommendation.incident_id.in_(incident_ids)))).scalars().all())
        if recommendation_ids:
            await db.execute(delete(Action).where(Action.recommendation_id.in_(recommendation_ids)))
        await db.execute(delete(Recommendation).where(Recommendation.incident_id.in_(incident_ids)))
        await db.execute(delete(incident_signals).where(incident_signals.c.incident_id.in_(incident_ids)))
        await db.execute(delete(Incident).where(Incident.id.in_(incident_ids)))
    if signal_ids:
        await db.execute(delete(Signal).where(Signal.id.in_(signal_ids)))
    await db.execute(delete(Event).where(Event.scenario_run_id == run_id))
    await db.delete(run)
    return {"status": "success", "run_id": run_id, "deleted_event_count": len(event_ids)}


@router.post("/incidents/{id}/decision")
async def submit_decision(
    id: int, payload: DecisionPayload, db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_manager_key),
):
    """
    Submits a manager action decision (Approve, Reject, or Edit).
    """
    # 1. Enforce idempotency
    action_check = await db.execute(
        select(Action).filter(Action.idempotency_key == payload.idempotency_key)
    )
    existing_action = action_check.scalars().first()
    if existing_action:
        logger.info(
            f"Duplicate decision submitted for key {payload.idempotency_key}. Returning original action."
        )
        return {"status": "success", "action_id": existing_action.id, "duplicate": True}

    # 2. Query Incident and Recommendations
    stmt = (
        select(Incident)
        .join(Restaurant).filter(Incident.id == id).where(organization_filter(user))
        .options(selectinload(Incident.recommendations))
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not incident.recommendations:
        raise HTTPException(
            status_code=400, detail="No recommendations found for this incident."
        )

    rec = incident.recommendations[0]

    expires_at = rec.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if now_utc >= expires_at:
        raise HTTPException(status_code=409, detail="Recommendation has expired")
    if payload.decision == "EDIT" and not payload.final_action_text:
        raise HTTPException(
            status_code=422, detail="final_action_text is required for EDIT"
        )

    # 3. Create Action record
    new_action = Action(
        recommendation_id=rec.id,
        decision=payload.decision,
        suggested_text=rec.action_text,
        final_text=payload.final_action_text or rec.action_text,
        decided_by=user.subject,
        manager_note=payload.manager_note,
        idempotency_key=payload.idempotency_key,
        decided_at=now_utc,
    )

    if payload.decision in ["APPROVE", "EDIT"]:
        incident.status = "APPROVED_PENDING_EXECUTION"  # type: ignore[assignment]
        new_action.execution_status = "PENDING"  # type: ignore[assignment]
    else:
        incident.status = "ACTION_REJECTED"  # type: ignore[assignment]
        new_action.execution_status = "NOT_APPLICABLE"  # type: ignore[assignment]

    db.add(new_action)
    await db.flush()

    # 4. Broadcast transition via WebSockets
    await manager.broadcast_transition(
        {
            "message_id": f"msg_dec_{new_action.id}",
            "incident_id": incident.id,
            "stage": incident.status,
            "status": "success",
            "occurred_at": now_utc.isoformat(),
        }
    )

    return {"status": "success", "action_id": new_action.id, "duplicate": False}


@router.post("/actions/{id}/execution")
async def acknowledge_execution(id: int, db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_manager_key)):
    action = (await db.execute(
        select(Action).join(Recommendation).join(Incident).join(Restaurant).where(
            Action.id == id, organization_filter(user)).options(
            selectinload(Action.recommendation).selectinload(Recommendation.incident)
        )
    )).scalars().first()
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.decision not in {"APPROVE", "EDIT"}:
        raise HTTPException(status_code=409, detail="Rejected action cannot be executed")
    action.execution_status = "EXECUTED"
    action.executed_at = datetime.datetime.now(datetime.timezone.utc)
    incident = action.recommendation.incident
    incident.status = "ACTION_EXECUTED"
    await db.flush()
    return {"status": "success", "action_id": action.id, "execution_status": "EXECUTED"}


@router.get("/incidents/{id}/outcome")
async def get_outcome(id: int, db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    result = await db.execute(select(Outcome).join(Incident).join(Restaurant).where(
        Outcome.incident_id == id, organization_filter(user)))
    outcome = result.scalars().first()
    if outcome is None:
        raise HTTPException(status_code=404, detail="Outcome not yet available")
    return outcome


@router.post("/incidents/{id}/verify")
async def verify_outcome(id: int, db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_manager_key)):
    incident = (
        (await db.execute(select(Incident).join(Restaurant).where(Incident.id == id,
            organization_filter(user)))).scalars().first()
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status not in {"ACTION_EXECUTED", "VERIFYING"}:
        raise HTTPException(status_code=409, detail="Incident is not ready to verify")
    outcome = await verify_incident_outcome(db, incident)
    await manager.broadcast_transition(
        {
            "message_id": f"msg_outcome_{outcome.id}",
            "incident_id": incident.id,
            "stage": incident.status,
            "status": outcome.status,
            "occurred_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    return outcome


@router.get("/analytics/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db_session), user: UserContext = Depends(require_user)):
    outlet_ids = select(Restaurant.id).where(organization_filter(user))
    incident_count = await db.scalar(select(func.count(Incident.id)).where(Incident.restaurant_id.in_(outlet_ids)))
    active_count = await db.scalar(
        select(func.count(Incident.id)).where(
            Incident.status.not_in(("RESOLVED", "ACTION_REJECTED", "NOT_IMPROVED")), Incident.restaurant_id.in_(outlet_ids)
        )
    )
    resolved_count = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status == "RESOLVED", Incident.restaurant_id.in_(outlet_ids))
    )
    exposure = await db.scalar(select(func.sum(Incident.revenue_at_risk)).where(Incident.restaurant_id.in_(outlet_ids)))
    return {
        "incident_count": incident_count or 0,
        "active_incident_count": active_count or 0,
        "resolved_incident_count": resolved_count or 0,
        "estimated_exposure": exposure or 0,
        "synthetic": False if settings.SERVERLESS_MODE else True,
    }


@router.post("/demo/reset")
async def reset_demo(db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_key)):
    """
    Cleans synthetic run-derived records from the tables to support clean repeatable scenarios.
    """
    if not settings.DEMO_MODE or not settings.ALLOW_GLOBAL_DEMO_RESET:
        raise HTTPException(status_code=403, detail="Demo reset is disabled")
    logger.info("Executing demo database reset.")
    try:
        # Delete dependencies first to respect FK constraints
        await db.execute(delete(PredictiveEvaluationRecord))
        await db.execute(delete(ActualOutcomeRecord))
        await db.execute(delete(DecisionTraceRecord))
        await db.execute(delete(GuardResultRecord))
        await db.execute(delete(PredictiveDecisionRecord))
        await db.execute(delete(ForecastDossierRecord))
        await db.execute(delete(DriverEvidenceRecord))
        await db.execute(delete(RiskCandidateRecord))
        await db.execute(delete(CapacityProjectionRecord))
        await db.execute(delete(InventoryProjectionRecord))
        await db.execute(delete(ForecastRecord))
        await db.execute(delete(PredictiveFeatureSnapshot))
        await db.execute(delete(ForecastModelArtifactRecord))
        await db.execute(delete(Outcome))
        await db.execute(delete(Action))
        await db.execute(delete(Recommendation))
        await db.execute(delete(incident_signals))
        await db.execute(delete(Incident))
        await db.execute(delete(Signal))
        await db.execute(delete(Event))
        await db.execute(delete(ScenarioRun))
        await db.execute(delete(Restaurant).where(Restaurant.synthetic.is_(True)))

        return {"status": "success", "detail": "Demo database reset successful."}
    except Exception as e:
        logger.error(f"Reset database failed: {e}")
        raise HTTPException(status_code=500, detail="Database reset failed")


# WebSocket Endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket channel for fanning out operational stage changes.
    """
    if settings.SERVERLESS_MODE:
        await websocket.close(code=1008); return
    origin = websocket.headers.get("origin")
    allowed = {item.strip() for item in settings.WS_ALLOWED_ORIGINS.split(",") if item.strip()}
    protocols = {item.strip() for item in websocket.headers.get("sec-websocket-protocol", "").split(",")}
    if origin not in allowed or not settings.MANAGER_API_KEY or settings.MANAGER_API_KEY not in protocols:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, subprotocol=settings.MANAGER_API_KEY)
    try:
        while True:
            # Keep connection alive by waiting for messages (or ignoring them for MVP)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)
