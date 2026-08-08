"""Deterministic signal correlation engine."""

from __future__ import annotations

from datetime import timezone

from lossline_intelligence.correlation.rules import (
    ALL_CORRELATED_TYPES,
    CORRELATION_RULE_ID,
    CORRELATION_RULE_VERSION,
    MAX_GAP_MINUTES,
    REQUIRED_SIGNAL_TYPES,
    SUPPORTING_SIGNAL_TYPES,
)
from lossline_intelligence.models.incident import (
    IncidentCandidate,
    IncidentType,
    ProbableCauseCategory,
)
from lossline_intelligence.models.signal import Signal, SignalType


def _minutes_between(a, b) -> float:
    return abs((a - b).total_seconds()) / 60.0


def _dedupe_signals(signals: list[Signal]) -> list[Signal]:
    """Keep first occurrence per signal_id; ignore exact duplicates."""
    seen: set[str] = set()
    unique: list[Signal] = []
    for sig in signals:
        if sig.signal_id in seen:
            continue
        seen.add(sig.signal_id)
        unique.append(sig)
    return unique


def _pick_one_per_type(signals: list[Signal]) -> dict[SignalType, Signal]:
    """Select one signal per type (earliest window_start wins)."""
    by_type: dict[SignalType, Signal] = {}
    for sig in sorted(signals, key=lambda s: s.window_start):
        if sig.signal_type not in by_type:
            by_type[sig.signal_type] = sig
    return by_type


def _temporally_aligned(signals: list[Signal], max_gap_minutes: float) -> bool:
    if not signals:
        return False
    earliest_start = min(s.window_start for s in signals)
    return all(
        _minutes_between(sig.window_end, earliest_start) <= max_gap_minutes
        for sig in signals
    )


def _build_candidate_id(outlet_id: str, window_start, rule_version: str) -> str:
    tag = window_start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"inc_{outlet_id}_{IncidentType.OPERATIONAL_OVERLOAD}_{tag}_{rule_version}"


def _union_evidence(signals: list[Signal]) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for sig in signals:
        for eid in sig.evidence_event_ids:
            if eid not in seen:
                seen.add(eid)
                ids.append(eid)
    return tuple(ids)


def correlate_signals(
    signals: list[Signal],
    *,
    max_gap_minutes: float = MAX_GAP_MINUTES,
) -> IncidentCandidate | None:
    """Apply M1 operational-overload correlation to a list of signals.

    Returns the first qualifying candidate found (one outlet per call in M1).
    """
    if not signals:
        return None

    deduped = _dedupe_signals(signals)

    by_outlet: dict[str, list[Signal]] = {}
    for sig in deduped:
        if sig.signal_type not in ALL_CORRELATED_TYPES:
            continue
        by_outlet.setdefault(sig.outlet_id, []).append(sig)

    for outlet_id, outlet_signals in by_outlet.items():
        candidate = _evaluate_outlet(
            outlet_id, outlet_signals, max_gap_minutes=max_gap_minutes
        )
        if candidate is not None:
            return candidate

    return None


def _evaluate_outlet(
    outlet_id: str,
    signals: list[Signal],
    *,
    max_gap_minutes: float,
) -> IncidentCandidate | None:
    by_type = _pick_one_per_type(signals)

    required = [by_type[t] for t in REQUIRED_SIGNAL_TYPES if t in by_type]
    if len(required) != len(REQUIRED_SIGNAL_TYPES):
        return None

    supporting = [by_type[t] for t in SUPPORTING_SIGNAL_TYPES if t in by_type]
    all_correlated = required + supporting

    if not _temporally_aligned(all_correlated, max_gap_minutes):
        return None

    required_tuple = tuple(sorted(required, key=lambda s: s.window_start))
    supporting_tuple = tuple(sorted(supporting, key=lambda s: s.window_start))
    window_start = min(s.window_start for s in all_correlated)
    window_end = max(s.window_end for s in all_correlated)

    return IncidentCandidate(
        candidate_id=_build_candidate_id(
            outlet_id, window_start, CORRELATION_RULE_VERSION
        ),
        outlet_id=outlet_id,
        incident_type=IncidentType.OPERATIONAL_OVERLOAD,
        probable_cause_category=ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        required_signals=required_tuple,
        supporting_signals=supporting_tuple,
        evidence_event_ids=_union_evidence(all_correlated),
        window_start=window_start,
        window_end=window_end,
        correlation_rule_id=CORRELATION_RULE_ID,
        correlation_rule_version=CORRELATION_RULE_VERSION,
    )
