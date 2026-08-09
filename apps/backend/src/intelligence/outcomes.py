"""Deterministic post-action outcome verification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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

    pre_result = await db.execute(
        select(Event).where(
            Event.restaurant_id == incident.restaurant_id,
            Event.occurred_at >= incident.window_start,
            Event.occurred_at < incident.window_end,
        )
    )
    pre_events = pre_result.scalars().all()
    result = await db.execute(
        select(Event).where(
            Event.restaurant_id == incident.restaurant_id,
            Event.occurred_at > incident.window_end,
        )
    )
    events = result.scalars().all()
    def metrics(rows: list[Event]) -> dict[str, Any]:
        created_ids = {row.entity.get("id") for row in rows if row.event_type == "order.created"}
        cancelled = sum(
            row.event_type == "order.cancelled" and row.entity.get("id") in created_ids
            for row in rows
        )
        handoffs = [float(row.data["wait_seconds"]) / 60 for row in rows
                    if row.event_type == "delivery.handoff_completed"]
        prep = [float(row.data["duration_seconds"]) / 60 for row in rows
                if row.event_type == "preparation.completed"]
        count = len(created_ids)
        return {"order_count": count, "cancelled_order_count": cancelled,
            "cancellation_rate": cancelled / count if count else None,
            "avg_handoff_wait_minutes": sum(handoffs) / len(handoffs) if handoffs else None,
            "handoff_sample_count": len(handoffs),
            "avg_prep_minutes": sum(prep) / len(prep) if prep else None,
            "prep_sample_count": len(prep), "source_event_count": len(rows)}

    baseline_metrics = metrics(pre_events)
    post_metrics = metrics(events)
    sufficient = (
        baseline_metrics["order_count"] >= settings.OUTCOME_MIN_EVENTS
        and post_metrics["order_count"] >= settings.OUTCOME_MIN_EVENTS
    )
    improvements: list[bool] = []
    regressions: list[bool] = []
    for name, absolute_delta in (("cancellation_rate", 0.02),
                                 ("avg_prep_minutes", None),
                                 ("avg_handoff_wait_minutes", None)):
        before, after = baseline_metrics[name], post_metrics[name]
        if before is None or after is None:
            continue
        if absolute_delta is not None:
            improvements.append(before - after >= absolute_delta)
            regressions.append(after - before >= absolute_delta)
        elif before > 0:
            improvements.append((before - after) / before >= 0.10)
            regressions.append((after - before) / before >= 0.10)
    if not sufficient or not improvements:
        status = "INSUFFICIENT_DATA"
    elif any(regressions):
        status = "WORSENED"
    elif any(improvements):
        status = "IMPROVED"
    else:
        status = "NO_CHANGE"
    post_metrics["sufficient"] = sufficient
    post_metrics["non_causality_note"] = (
        "Observed pre/post association only; this evaluation does not establish causation."
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
    outcome.rule_version = "reactive_outcome.v2"
    if status == "IMPROVED":
        incident.status = "RESOLVED"
    elif status in {"NO_CHANGE", "WORSENED"}:
        incident.status = "NOT_IMPROVED"
    else:
        incident.status = "VERIFYING"
    await db.flush()
    return outcome
