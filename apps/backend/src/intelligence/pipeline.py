"""Deterministic detection pipeline: events → snapshot → detectors → persist.

LangGraph investigation / approval is intentionally NOT invoked here.
It starts only after an IncidentCandidate exists (Phase 3 — deferred).
"""

from __future__ import annotations

import logging
from dataclasses import fields
from decimal import Decimal
from contextlib import asynccontextmanager
from enum import Enum
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lossline_intelligence.aggregation import (
    BASELINE_VERSION,
    BaselineResult,
    MetricBaseline,
    MetricSnapshot,
    build_metric_snapshot,
    compute_baseline,
)
from lossline_intelligence.correlation import correlate_signals
from lossline_intelligence.detectors import (
    detect_cancellation_spike,
    detect_delay_review_spike,
    detect_handoff_delay_spike,
    detect_order_volume_spike,
    detect_prep_time_spike,
)
from lossline_intelligence.models.signal import Signal as DomainSignal
from lossline_intelligence.recommendations import (
    RecommendationAbstention,
    recommend,
)
from lossline_intelligence.scoring import (
    ConfidenceTier,
    RevenueInputs,
    compute_confidence,
    estimate_revenue_at_risk,
)

from src.config import settings
from src.db.models import Restaurant
from src.db.session import SessionLocal
from src.ingestion.schemas import EventEnvelope
from src.intelligence.event_loader import load_events_spanning, load_normalized_events
from src.intelligence.persistence import (
    broadcast_incident_transition,
    persist_incident_from_candidate,
    persist_m0_cancellation_incident,
    upsert_signal,
)
from src.intelligence.windows import analysis_window, prior_windows
from src.intelligence.langgraph_workflow import run_investigation

logger = logging.getLogger(__name__)


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _dataclass_json(value) -> dict:
    values = {field.name: getattr(value, field.name) for field in fields(value)}
    return _json_safe(values)


def _mb(median: Decimal | None, *, sample_count: int = 4) -> MetricBaseline:
    return MetricBaseline(
        median=median,
        mad=Decimal("0.5000") if median is not None else None,
        sample_count=sample_count if median is not None else 0,
    )


def fixture_baseline(outlet_id: str) -> BaselineResult:
    """CONFIG_DEFAULT M0 fixture baseline when historical windows are sparse."""
    cancel = Decimal(str(settings.M0_FIXTURE_CANCELLATION_RATE))
    orders = Decimal(str(settings.M0_FIXTURE_ORDER_COUNT))
    prep = Decimal(str(settings.M0_FIXTURE_AVG_PREP_MINUTES))
    handoff = Decimal(str(settings.M0_FIXTURE_AVG_HANDOFF_MINUTES))
    n = settings.BASELINE_HISTORY_WINDOWS
    return BaselineResult(
        outlet_id=outlet_id,
        sample_count=n,
        sufficient_history=True,
        baseline_version=f"{BASELINE_VERSION}+m0_fixture",
        order_count=_mb(orders, sample_count=n),
        cancellation_rate=_mb(cancel, sample_count=n),
        avg_prep_minutes=_mb(prep, sample_count=n),
        p90_prep_minutes=_mb(prep * Decimal("1.2"), sample_count=n),
        avg_handoff_wait_minutes=_mb(handoff, sample_count=n),
        negative_review_rate=_mb(Decimal("0.1000"), sample_count=n),
        delay_review_rate=_mb(Decimal("0.0500"), sample_count=n),
    )


def merge_baseline_with_fixture(
    computed: BaselineResult,
    fixture: BaselineResult,
) -> BaselineResult:
    """Prefer computed medians; fill gaps from the M0 fixture."""

    def pick(computed_mb: MetricBaseline, fixture_mb: MetricBaseline) -> MetricBaseline:
        if computed_mb.median is not None:
            return computed_mb
        return fixture_mb

    return BaselineResult(
        outlet_id=computed.outlet_id,
        sample_count=max(computed.sample_count, fixture.sample_count),
        sufficient_history=True,
        baseline_version=f"{computed.baseline_version}+fixture_fill",
        order_count=pick(computed.order_count, fixture.order_count),
        cancellation_rate=pick(computed.cancellation_rate, fixture.cancellation_rate),
        avg_prep_minutes=pick(computed.avg_prep_minutes, fixture.avg_prep_minutes),
        p90_prep_minutes=pick(computed.p90_prep_minutes, fixture.p90_prep_minutes),
        avg_handoff_wait_minutes=pick(
            computed.avg_handoff_wait_minutes, fixture.avg_handoff_wait_minutes
        ),
        negative_review_rate=pick(
            computed.negative_review_rate, fixture.negative_review_rate
        ),
        delay_review_rate=pick(computed.delay_review_rate, fixture.delay_review_rate),
    )


def run_detectors(
    snapshot: MetricSnapshot,
    baseline: BaselineResult,
) -> list[DomainSignal]:
    """Run all five M1 detectors; return emitted signals only."""
    detectors = (
        detect_order_volume_spike,
        detect_prep_time_spike,
        detect_handoff_delay_spike,
        detect_cancellation_spike,
        detect_delay_review_spike,
    )
    signals: list[DomainSignal] = []
    for detect in detectors:
        result = detect(snapshot, baseline)
        if result is not None:
            signals.append(result)
    return signals


def _avg_order_value(
    snapshot: MetricSnapshot, events_amounts: list[Decimal]
) -> Decimal | None:
    if not events_amounts:
        return None
    total = sum(events_amounts, Decimal("0"))
    return (total / Decimal(len(events_amounts))).quantize(Decimal("0.01"))


async def _resolve_currency(db: AsyncSession, restaurant_id: str) -> str:
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalars().first()
    return restaurant.currency if restaurant and restaurant.currency else "INR"


@asynccontextmanager
async def _pipeline_session(existing=None):
    if existing is not None:
        yield existing
    else:
        async with SessionLocal() as session:
            yield session


async def run_detection_pipeline(envelope: EventEnvelope, *, db_session=None) -> None:
    """Process one streamed event through deterministic intelligence + persist."""
    restaurant_id = envelope.restaurant_id
    outlet_id = restaurant_id  # identity mapping at the intelligence boundary
    window_start, window_end = analysis_window(envelope.occurred_at)

    async with _pipeline_session(db_session) as db:
        current_events = await load_normalized_events(
            db,
            restaurant_id=restaurant_id,
            window_start=window_start,
            window_end=window_end,
        )
        # Ensure the triggering event is included even if read-your-writes lags
        from src.intelligence.mapper import envelope_to_normalized

        trigger = envelope_to_normalized(envelope)
        if all(e.event_id != trigger.event_id for e in current_events):
            current_events = [*current_events, trigger]

        snapshot = build_metric_snapshot(
            current_events,
            outlet_id=outlet_id,
            window_start=window_start,
            window_end=window_end,
        )

        # Historical windows for baseline
        history_specs = prior_windows(
            window_start, count=settings.BASELINE_HISTORY_WINDOWS
        )
        historical_snapshots: list[MetricSnapshot] = []
        if history_specs:
            range_start = history_specs[0][0]
            range_end = window_start
            spanning = await load_events_spanning(
                db,
                restaurant_id=restaurant_id,
                range_start=range_start,
                range_end=range_end,
            )
            for hist_start, hist_end in history_specs:
                hist_snap = build_metric_snapshot(
                    spanning,
                    outlet_id=outlet_id,
                    window_start=hist_start,
                    window_end=hist_end,
                )
                # Only keep windows that had some activity
                if hist_snap.source_event_ids:
                    historical_snapshots.append(hist_snap)

        computed = compute_baseline(
            historical_snapshots,
            outlet_id=outlet_id,
            min_history_windows=settings.BASELINE_HISTORY_WINDOWS,
        )
        baseline = merge_baseline_with_fixture(computed, fixture_baseline(outlet_id))

        domain_signals = run_detectors(snapshot, baseline)
        if not domain_signals:
            logger.info(
                "[Detection Pipeline] No signals for %s window %s–%s",
                outlet_id,
                window_start.isoformat(),
                window_end.isoformat(),
            )
            await db.commit()
            return

        signal_rows = []
        cancel_domain: DomainSignal | None = None
        for sig in domain_signals:
            row = await upsert_signal(db, sig)
            signal_rows.append(row)
            if sig.signal_type.value == "CANCELLATION_SPIKE":
                cancel_domain = sig

        # Full M1 correlation path
        # Load recent persisted domain-compatible signals from this window set:
        # correlate using freshly detected signals (same window / outlet).
        candidate = correlate_signals(domain_signals)

        currency = await _resolve_currency(db, restaurant_id)

        if candidate is not None:
            confidence = compute_confidence(candidate)
            amounts = [e.amount for e in current_events if e.amount is not None]
            aov = _avg_order_value(snapshot, amounts)
            window_minutes = max(
                1.0,
                (snapshot.window_end - snapshot.window_start).total_seconds() / 60.0,
            )
            order_rate = Decimal(snapshot.order_count) / Decimal(str(window_minutes))
            # Observed cancelled value: approximate from cancelled count * AOV
            observed = None
            if aov is not None:
                observed = (aov * Decimal(snapshot.cancelled_order_count)).quantize(
                    Decimal("0.01")
                )

            cancel_sig = next(
                (
                    s
                    for s in domain_signals
                    if s.signal_type.value == "CANCELLATION_SPIKE"
                ),
                None,
            )
            revenue = estimate_revenue_at_risk(
                RevenueInputs(
                    observed_cancelled_value=observed,
                    current_cancel_rate=(
                        cancel_sig.current_value
                        if cancel_sig
                        else snapshot.cancellation_rate
                    ),
                    baseline_cancel_rate=(
                        cancel_sig.baseline_value
                        if cancel_sig
                        else baseline.cancellation_rate.median
                    ),
                    current_order_rate_per_min=order_rate,
                    avg_order_value=aov,
                    currency=currency,
                )
            )

            rec_result = recommend(candidate, confidence.score)
            domain_rec = (
                None if isinstance(rec_result, RecommendationAbstention) else rec_result
            )

            investigation = await run_investigation(
                candidate_id=candidate.candidate_id,
                outlet_id=candidate.outlet_id,
                incident_type=candidate.incident_type.value,
                signals=[
                    {
                        "signal_type": signal.signal_type.value,
                        "current_value": str(signal.current_value),
                        "baseline_value": str(signal.baseline_value),
                        "unit": signal.unit,
                    }
                    for signal in candidate.signals
                ],
                confidence=confidence.score,
                confidence_components={
                    "severity_component": confidence.severity_component,
                    "coverage_component": confidence.coverage_component,
                    "alignment_component": confidence.alignment_component,
                    "data_quality_component": confidence.data_quality_component,
                },
                revenue_risk=_dataclass_json(revenue),
                recommendation=(
                    _dataclass_json(domain_rec) if domain_rec is not None else None
                ),
            )
            status = investigation["status"]

            # Map signal rows that belong to the candidate
            candidate_signal_ids = {s.signal_id for s in candidate.signals}
            linked_rows = [
                row
                for row, domain in zip(signal_rows, domain_signals)
                if domain.signal_id in candidate_signal_ids
            ]

            incident = await persist_incident_from_candidate(
                db,
                candidate=candidate,
                signal_rows=linked_rows,
                confidence=confidence,
                revenue=revenue,
                recommendation=domain_rec,
                status=status,
                currency=currency,
                explanation=investigation["explanation"],
                explanation_source=investigation["explanation_source"],
                explanation_provider_model=investigation[
                    "explanation_provider_model"
                ],
            )
            await db.commit()
            await broadcast_incident_transition(incident, status)
            logger.info(
                "[Detection Pipeline] Persisted overload incident %s status=%s",
                incident.id,
                status,
            )
            return

        # M0 path: cancellation signal alone still surfaces an incident
        if cancel_domain is not None:
            cancel_row = next(
                row
                for row, domain in zip(signal_rows, domain_signals)
                if domain.signal_id == cancel_domain.signal_id
            )
            incident = await persist_m0_cancellation_incident(
                db,
                domain_signal=cancel_domain,
                signal_row=cancel_row,
            )
            await db.commit()
            await broadcast_incident_transition(incident, incident.status)
            logger.info(
                "[Detection Pipeline] Persisted M0 cancellation incident %s",
                incident.id,
            )
            return

        await db.commit()
        logger.info(
            "[Detection Pipeline] Persisted %d signal(s) without incident for %s",
            len(signal_rows),
            outlet_id,
        )
