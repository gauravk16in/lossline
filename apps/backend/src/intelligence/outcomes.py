"""Deterministic post-action outcome verification."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import Event, Incident, Outcome


async def verify_incident_outcome(db: AsyncSession, incident: Incident) -> Outcome:
    """Compare recovery events with the incident window and persist one outcome."""
    existing = (
        (await db.execute(select(Outcome).where(Outcome.incident_id == incident.id)))
        .scalars()
        .first()
    )
    # Terminal outcomes are immutable. INSUFFICIENT_DATA is provisional: a
    # manager may verify before enough recovery events arrive, then retry once
    # the simulator has supplied additional evidence.
    if existing is not None and existing.status != "INSUFFICIENT_DATA":
        return existing

    result = await db.execute(
        select(Event).where(
            Event.restaurant_id == incident.restaurant_id,
            Event.occurred_at > incident.window_end,
        )
    )
    events = result.scalars().all()
    created = sum(event.event_type == "order.created" for event in events)
    cancelled = sum(event.event_type == "order.cancelled" for event in events)
    cancellation_rate = cancelled / created if created else None
    handoffs = [
        float(event.data["wait_seconds"]) / 60
        for event in events
        if event.event_type == "delivery.handoff_completed"
    ]
    prep = [
        float(event.data["duration_seconds"]) / 60
        for event in events
        if event.event_type == "preparation.completed"
    ]

    post_metrics = {
        "order_count": created,
        "cancelled_order_count": cancelled,
        "cancellation_rate": cancellation_rate,
        "avg_handoff_wait_minutes": sum(handoffs) / len(handoffs) if handoffs else None,
        "avg_prep_minutes": sum(prep) / len(prep) if prep else None,
        "source_event_count": len(events),
    }
    baseline_metrics = {
        "incident_confidence": incident.confidence,
        "incident_severity": incident.severity,
        "window_start": incident.window_start.isoformat(),
        "window_end": incident.window_end.isoformat(),
    }
    sufficient = len(events) >= settings.OUTCOME_MIN_EVENTS and created > 0
    improved = sufficient and cancelled == 0
    status = (
        "IMPROVED"
        if improved
        else ("NOT_IMPROVED" if sufficient else "INSUFFICIENT_DATA")
    )
    now = datetime.now(timezone.utc)
    if existing is None:
        outcome = Outcome(incident_id=incident.id)
        db.add(outcome)
    else:
        outcome = existing
    outcome.status = status
    outcome.baseline_metrics = baseline_metrics
    outcome.post_metrics = post_metrics
    outcome.check_after = now
    outcome.evaluated_at = now if sufficient else None
    outcome.rule_version = "outcome.v1"
    if status == "IMPROVED":
        incident.status = "RESOLVED"
    elif status == "NOT_IMPROVED":
        incident.status = "NOT_IMPROVED"
    else:
        incident.status = "VERIFYING"
    await db.flush()
    return outcome
