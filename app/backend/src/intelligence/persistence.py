"""Idempotent persistence of domain Signals / Incidents / Recommendations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lossline_intelligence.models.incident import IncidentCandidate
from lossline_intelligence.models.signal import Signal as DomainSignal
from lossline_intelligence.recommendations.engine import Recommendation as DomainRecommendation
from lossline_intelligence.scoring.confidence import ConfidenceResult
from lossline_intelligence.scoring.revenue_risk import RevenueRiskEstimate, RevenueStatus

from src.config import settings
from src.db.models import Incident, Recommendation, Signal, incident_signals
from src.realtime.websocket import manager

logger = logging.getLogger(__name__)

_OPEN_STATUSES = frozenset(
    {
        "DETECTED",
        "INVESTIGATING",
        "AWAITING_APPROVAL",
        "ACTION_APPROVED",
        "MONITOR_ONLY",
        "VERIFYING",
    }
)


async def _link_signals(
    db: AsyncSession,
    incident_id: int,
    signal_rows: list[Signal],
) -> None:
    """Idempotently insert incident↔signal association rows (no lazy-load)."""
    if not signal_rows:
        return
    existing = await db.execute(
        select(incident_signals.c.signal_id).where(
            incident_signals.c.incident_id == incident_id
        )
    )
    have = set(existing.scalars().all())
    for row in signal_rows:
        if row.id in have:
            continue
        await db.execute(
            incident_signals.insert().values(
                incident_id=incident_id, signal_id=row.id
            )
        )


async def upsert_signal(db: AsyncSession, domain: DomainSignal) -> Signal:
    """Insert or update a Signal row keyed by unique window/type/outlet."""
    stmt = select(Signal).where(
        Signal.restaurant_id == domain.outlet_id,
        Signal.signal_type == domain.signal_type.value,
        Signal.window_start == domain.window_start,
        Signal.window_end == domain.window_end,
    )
    result = await db.execute(stmt)
    row = result.scalars().first()

    evidence = list(domain.evidence_event_ids)
    if row is None:
        row = Signal(
            restaurant_id=domain.outlet_id,
            signal_type=domain.signal_type.value,
            severity=domain.severity,
            current_value=float(domain.current_value),
            baseline_value=float(domain.baseline_value),
            deviation=float(domain.deviation_ratio),
            unit=domain.unit,
            window_start=domain.window_start,
            window_end=domain.window_end,
            evidence_event_ids=evidence,
            detector_version=domain.detector_version,
        )
        db.add(row)
    else:
        row.severity = domain.severity
        row.current_value = float(domain.current_value)
        row.baseline_value = float(domain.baseline_value)
        row.deviation = float(domain.deviation_ratio)
        row.unit = domain.unit
        row.evidence_event_ids = evidence
        row.detector_version = domain.detector_version

    await db.flush()
    return row


async def find_open_incident(
    db: AsyncSession,
    *,
    restaurant_id: str,
    incident_type: str,
    window_end: datetime,
) -> Incident | None:
    """Find an open incident for dedup within INCIDENT_DEDUP_MINUTES."""
    cutoff = window_end - timedelta(minutes=settings.INCIDENT_DEDUP_MINUTES)
    stmt = (
        select(Incident)
        .options(selectinload(Incident.signals), selectinload(Incident.recommendations))
        .where(
            Incident.restaurant_id == restaurant_id,
            Incident.incident_type == incident_type,
            Incident.status.in_(tuple(_OPEN_STATUSES)),
            Incident.window_end >= cutoff,
        )
        .order_by(Incident.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def persist_incident_from_candidate(
    db: AsyncSession,
    *,
    candidate: IncidentCandidate,
    signal_rows: list[Signal],
    confidence: ConfidenceResult,
    revenue: RevenueRiskEstimate,
    recommendation: DomainRecommendation | None,
    status: str,
    currency: str = "INR",
) -> Incident:
    """Create or update an OPERATIONAL_OVERLOAD incident and optional recommendation."""
    now = datetime.now(timezone.utc)
    existing = await find_open_incident(
        db,
        restaurant_id=candidate.outlet_id,
        incident_type=candidate.incident_type.value,
        window_end=candidate.window_end,
    )

    severity = max((s.severity for s in candidate.signals), default=0.0)
    revenue_amount = (
        float(revenue.estimated_amount)
        if revenue.status == RevenueStatus.OK and revenue.estimated_amount is not None
        else None
    )
    components: dict[str, Any] = {
        "severity_component": confidence.severity_component,
        "coverage_component": confidence.coverage_component,
        "alignment_component": confidence.alignment_component,
        "data_quality_component": confidence.data_quality_component,
        "formula_version": confidence.formula_version,
        "tier": confidence.tier.value,
        "candidate_id": candidate.candidate_id,
    }

    if existing is None:
        incident = Incident(
            restaurant_id=candidate.outlet_id,
            incident_type=candidate.incident_type.value,
            status=status,
            severity=severity,
            confidence=confidence.score,
            confidence_components=components,
            probable_cause=candidate.probable_cause_category.value,
            explanation=None,  # LangGraph / LLM explain — deferred
            revenue_at_risk=revenue_amount,
            currency=currency,
            window_start=candidate.window_start,
            window_end=candidate.window_end,
            correlation_rule_version=candidate.correlation_rule_version,
            config_version=settings.CONFIG_VERSION,
            created_at=now,
            updated_at=now,
        )
        db.add(incident)
        await db.flush()
    else:
        incident = existing
        incident.status = status
        incident.severity = severity
        incident.confidence = confidence.score
        incident.confidence_components = components
        incident.probable_cause = candidate.probable_cause_category.value
        incident.revenue_at_risk = revenue_amount
        incident.currency = currency
        # Expand window to cover new evidence
        if candidate.window_start < incident.window_start:
            incident.window_start = candidate.window_start
        if candidate.window_end > incident.window_end:
            incident.window_end = candidate.window_end
        incident.correlation_rule_version = candidate.correlation_rule_version
        incident.config_version = settings.CONFIG_VERSION
        incident.updated_at = now

    await _link_signals(db, incident.id, signal_rows)

    if recommendation is not None:
        await _upsert_recommendation(db, incident, recommendation)

    await db.flush()
    return incident


async def persist_m0_cancellation_incident(
    db: AsyncSession,
    *,
    domain_signal: DomainSignal,
    signal_row: Signal,
) -> Incident:
    """M0 fallback: persist a thin incident from a single cancellation signal.

    Used when full overload correlation has not yet fired, so the vertical
    slice still surfaces a detectable signal via REST/WS.
    """
    now = datetime.now(timezone.utc)
    incident_type = "CANCELLATION_SPIKE"
    existing = await find_open_incident(
        db,
        restaurant_id=domain_signal.outlet_id,
        incident_type=incident_type,
        window_end=domain_signal.window_end,
    )
    components = {
        "source": "m0_cancellation_detector",
        "detector_version": domain_signal.detector_version,
        "signal_id": domain_signal.signal_id,
    }
    if existing is None:
        incident = Incident(
            restaurant_id=domain_signal.outlet_id,
            incident_type=incident_type,
            status="AWAITING_APPROVAL",
            severity=domain_signal.severity,
            confidence=min(0.95, domain_signal.severity),
            confidence_components=components,
            probable_cause="CANCELLATION_RATE_SPIKE",
            explanation=(
                f"Cancellation rate spiked to {float(domain_signal.current_value):.1%} "
                f"vs baseline {float(domain_signal.baseline_value):.1%}."
            ),
            revenue_at_risk=None,
            currency="INR",
            window_start=domain_signal.window_start,
            window_end=domain_signal.window_end,
            correlation_rule_version="m0_cancellation_v1",
            config_version=settings.CONFIG_VERSION,
            created_at=now,
            updated_at=now,
        )
        db.add(incident)
        await db.flush()
    else:
        incident = existing
        incident.severity = max(incident.severity, domain_signal.severity)
        incident.confidence = min(0.95, incident.severity)
        incident.confidence_components = components
        incident.updated_at = now

    await _link_signals(db, incident.id, [signal_row])
    await db.flush()
    return incident


async def _upsert_recommendation(
    db: AsyncSession,
    incident: Incident,
    recommendation: DomainRecommendation,
) -> Recommendation:
    stmt = select(Recommendation).where(
        Recommendation.incident_id == incident.id,
        Recommendation.rule_id == recommendation.rule_id,
    )
    result = await db.execute(stmt)
    row = result.scalars().first()

    expected_impact = [
        {
            "metric": e.metric,
            "direction": e.direction,
            "note": e.note,
        }
        for e in recommendation.expected_effect
    ]
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    if row is None:
        row = Recommendation(
            incident_id=incident.id,
            rule_id=recommendation.rule_id,
            action_text=recommendation.action_text,
            expected_impact=expected_impact,
            urgency=recommendation.urgency,
            risk_tier=recommendation.risk_level.value
            if hasattr(recommendation.risk_level, "value")
            else str(recommendation.risk_level),
            source=recommendation.source,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        row.action_text = recommendation.action_text
        row.expected_impact = expected_impact
        row.urgency = recommendation.urgency
        row.risk_tier = (
            recommendation.risk_level.value
            if hasattr(recommendation.risk_level, "value")
            else str(recommendation.risk_level)
        )
        row.source = recommendation.source
        row.expires_at = expires_at

    await db.flush()
    return row


async def broadcast_incident_transition(incident: Incident, stage: str) -> None:
    """Fan out a display-safe WebSocket transition (REST remains authoritative)."""
    await manager.broadcast_transition(
        {
            "message_id": f"msg_inc_{incident.id}_{stage}",
            "incident_id": incident.id,
            "stage": stage,
            "status": "success",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
