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
from pydantic import BaseModel

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
)
from src.ingestion.schemas import EventEnvelope
from src.realtime.websocket import manager
from src.config import settings
from src.demo.entities import DEMO_RESTAURANTS
from src.intelligence.outcomes import verify_incident_outcome

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def compute_payload_hash(envelope: EventEnvelope) -> str:
    """
    Computes a stable deterministic SHA256 hash of the event envelope.
    """
    serialized = json.dumps(envelope.model_dump(), sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@router.post("/events", status_code=202)
async def ingest_event(
    envelope: EventEnvelope, db: AsyncSession = Depends(get_db_session)
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
            return {
                "event_id": envelope.event_id,
                "status": "accepted",
                "duplicate": True,
            }
        else:
            logger.warning(
                f"Conflict: Event {envelope.event_id} received with differing payload."
            )
            raise HTTPException(
                status_code=409,
                detail=f"Event ID {envelope.event_id} already exists with a different payload.",
            )

    # Auto-provision Restaurant if not exists to facilitate smooth simulator runs
    res_check = await db.execute(
        select(Restaurant).filter(Restaurant.id == envelope.restaurant_id)
    )
    restaurant = res_check.scalars().first()
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
    new_event = Event(
        event_id=envelope.event_id,
        restaurant_id=envelope.restaurant_id,
        source=envelope.source.value,
        event_type=envelope.event_type.value,
        occurred_at=envelope.occurred_at,
        entity=envelope.entity.model_dump(),
        data=envelope.data,
        metadata_json=envelope.metadata.model_dump(),
        schema_version=envelope.schema_version,
        payload_hash=p_hash,
        published_to_stream=False,
    )
    db.add(new_event)

    if settings.INLINE_PROCESSING:
        # Local no-infrastructure mode: preserve durability before deriving state.
        await db.commit()
        from src.intelligence.pipeline import run_detection_pipeline

        await run_detection_pipeline(envelope)

    return {"event_id": envelope.event_id, "status": "accepted", "duplicate": False}


@router.get("/restaurants")
async def get_restaurants(db: AsyncSession = Depends(get_db_session)):
    """
    Get all active restaurants and basic details.
    """
    result = await db.execute(select(Restaurant))
    return result.scalars().all()


@router.get("/incidents")
async def get_incidents(
    status: str | None = None, db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves the incident feed.
    """
    stmt = select(Incident)
    if status:
        stmt = stmt.filter(Incident.status == status)
    stmt = stmt.options(selectinload(Incident.recommendations)).order_by(
        Incident.created_at.desc()
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/incidents/{id}")
async def get_incident(id: int, db: AsyncSession = Depends(get_db_session)):
    """
    Retrieves full details of a specific incident, including associated signals and recommendations.
    """
    stmt = (
        select(Incident)
        .filter(Incident.id == id)
        .options(selectinload(Incident.signals), selectinload(Incident.recommendations))
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


class DecisionPayload(BaseModel):
    decision: Literal["APPROVE", "REJECT", "EDIT"]
    final_action_text: str | None = None
    manager_note: str | None = None
    idempotency_key: str


class ScenarioRunPayload(BaseModel):
    scenario_id: str = "meghana_lunch_rush_v1"
    seed: int = 42
    speed: float = 120.0


@router.post("/demo/runs", status_code=201)
async def create_demo_run(
    payload: ScenarioRunPayload, db: AsyncSession = Depends(get_db_session)
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
async def complete_demo_run(id: int, db: AsyncSession = Depends(get_db_session)):
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


@router.post("/incidents/{id}/decision")
async def submit_decision(
    id: int, payload: DecisionPayload, db: AsyncSession = Depends(get_db_session)
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
        .filter(Incident.id == id)
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
        decided_by="manager_1",  # A8: Default manager identity
        manager_note=payload.manager_note,
        idempotency_key=payload.idempotency_key,
        decided_at=now_utc,
    )

    if payload.decision in ["APPROVE", "EDIT"]:
        incident.status = "ACTION_APPROVED"  # type: ignore[assignment]
        new_action.execution_status = "EXECUTED"  # type: ignore[assignment]
        new_action.executed_at = now_utc  # type: ignore[assignment]
    else:
        incident.status = "ACTION_REJECTED"  # type: ignore[assignment]
        new_action.execution_status = "FAILED"  # type: ignore[assignment]

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


@router.get("/incidents/{id}/outcome")
async def get_outcome(id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Outcome).where(Outcome.incident_id == id))
    outcome = result.scalars().first()
    if outcome is None:
        raise HTTPException(status_code=404, detail="Outcome not yet available")
    return outcome


@router.post("/incidents/{id}/verify")
async def verify_outcome(id: int, db: AsyncSession = Depends(get_db_session)):
    incident = (
        (await db.execute(select(Incident).where(Incident.id == id))).scalars().first()
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status not in {"ACTION_APPROVED", "VERIFYING"}:
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
async def analytics_summary(db: AsyncSession = Depends(get_db_session)):
    incident_count = await db.scalar(select(func.count(Incident.id)))
    active_count = await db.scalar(
        select(func.count(Incident.id)).where(
            Incident.status.not_in(("RESOLVED", "ACTION_REJECTED", "NOT_IMPROVED"))
        )
    )
    resolved_count = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status == "RESOLVED")
    )
    exposure = await db.scalar(select(func.sum(Incident.revenue_at_risk)))
    return {
        "incident_count": incident_count or 0,
        "active_incident_count": active_count or 0,
        "resolved_incident_count": resolved_count or 0,
        "estimated_exposure": exposure or 0,
        "synthetic": True,
    }


@router.post("/demo/reset")
async def reset_demo(db: AsyncSession = Depends(get_db_session)):
    """
    Cleans synthetic run-derived records from the tables to support clean repeatable scenarios.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo reset is disabled")
    logger.info("Executing demo database reset.")
    try:
        # Delete dependencies first to respect FK constraints
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
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive by waiting for messages (or ignoring them for MVP)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)
