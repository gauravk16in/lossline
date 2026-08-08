"""Tests for the deterministic confidence scorer."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lossline_intelligence.scoring.confidence import (
    CONFIDENCE_CAP,
    ConfidenceTier,
    _classify_tier,
    compute_confidence,
)
from lossline_intelligence.models.incident import (
    IncidentCandidate,
    IncidentType,
    ProbableCauseCategory,
    QualityFlags,
)
from lossline_intelligence.models.signal import Signal, SignalType

_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_W_END = _W_START + timedelta(minutes=30)


def _signal(signal_type: SignalType, severity: float = 0.75) -> Signal:
    return Signal.model_validate(
        {
            "signal_id": f"sig_{signal_type}",
            "outlet_id": "store_test",
            "signal_type": signal_type,
            "severity": severity,
            "current_value": Decimal("10"),
            "baseline_value": Decimal("5"),
            "deviation_ratio": Decimal("1"),
            "unit": "unit",
            "window_start": _W_START,
            "window_end": _W_END,
            "evidence_event_ids": ("evt_001",),
            "detector_version": "test_v1",
        }
    )


def _full_candidate() -> IncidentCandidate:
    required = (
        _signal(SignalType.ORDER_VOLUME_SPIKE),
        _signal(SignalType.PREP_TIME_SPIKE),
        _signal(SignalType.CANCELLATION_SPIKE),
    )
    supporting = (
        _signal(SignalType.HANDOFF_DELAY_SPIKE),
        _signal(SignalType.DELAY_REVIEW_SPIKE),
    )
    return IncidentCandidate(
        candidate_id="inc_test",
        outlet_id="store_test",
        incident_type=IncidentType.OPERATIONAL_OVERLOAD,
        probable_cause_category=ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        required_signals=required,
        supporting_signals=supporting,
        evidence_event_ids=("evt_001",),
        window_start=_W_START,
        window_end=_W_END,
        correlation_rule_id="OPERATIONAL_OVERLOAD_V1",
        correlation_rule_version="overload_v1",
    )


def test_confidence_never_exceeds_cap() -> None:
    base = _full_candidate()
    saturated = IncidentCandidate(
        candidate_id="inc_saturated",
        outlet_id=base.outlet_id,
        incident_type=base.incident_type,
        probable_cause_category=base.probable_cause_category,
        required_signals=tuple(
            signal.model_copy(update={"severity": 1.0})
            for signal in base.required_signals
        ),
        supporting_signals=tuple(
            signal.model_copy(update={"severity": 1.0})
            for signal in base.supporting_signals
        ),
        evidence_event_ids=base.evidence_event_ids,
        window_start=base.window_start,
        window_end=base.window_start + timedelta(microseconds=1),
        correlation_rule_id=base.correlation_rule_id,
        correlation_rule_version=base.correlation_rule_version,
    )

    result = compute_confidence(saturated)

    assert result.score == CONFIDENCE_CAP
    assert result.confidence == CONFIDENCE_CAP


def test_all_components_in_unit_range() -> None:
    result = compute_confidence(_full_candidate())
    for component in (
        result.severity_component,
        result.coverage_component,
        result.alignment_component,
        result.data_quality_component,
    ):
        assert 0.0 <= component <= 1.0


def test_tier_assigned_from_score() -> None:
    result = compute_confidence(_full_candidate())
    assert result.tier is ConfidenceTier.HIGH
    assert result.formula_version == "confidence_v1"


def test_deterministic_replay() -> None:
    candidate = _full_candidate()
    r1 = compute_confidence(candidate)
    r2 = compute_confidence(candidate)
    assert r1 == r2


def test_poor_quality_lowers_confidence() -> None:
    """Low data quality should reduce confidence vs default quality=1.0."""
    good = compute_confidence(_full_candidate())
    bad_quality = QualityFlags(
        sample_sufficiency=0.2,
        baseline_sufficiency=0.2,
        freshness=0.2,
    )
    poor = compute_confidence(_full_candidate(), quality=bad_quality)
    assert poor.score < good.score


def test_full_coverage_higher_than_partial() -> None:
    """All 5 signal types present → higher coverage than 3 types."""
    full = compute_confidence(_full_candidate())

    partial_candidate = IncidentCandidate(
        candidate_id="inc_partial",
        outlet_id="store_test",
        incident_type=IncidentType.OPERATIONAL_OVERLOAD,
        probable_cause_category=ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        required_signals=(
            _signal(SignalType.ORDER_VOLUME_SPIKE),
            _signal(SignalType.PREP_TIME_SPIKE),
            _signal(SignalType.CANCELLATION_SPIKE),
        ),
        supporting_signals=(),
        evidence_event_ids=("evt_001",),
        window_start=_W_START,
        window_end=_W_END,
        correlation_rule_id="OPERATIONAL_OVERLOAD_V1",
        correlation_rule_version="overload_v1",
    )
    partial = compute_confidence(partial_candidate)
    assert full.score > partial.score


def test_tier_boundaries() -> None:
    assert _classify_tier(0.0) is ConfidenceTier.MONITOR_ONLY
    assert _classify_tier(0.499999) is ConfidenceTier.MONITOR_ONLY
    assert _classify_tier(0.50) is ConfidenceTier.REVIEW_REQUIRED
    assert _classify_tier(0.749999) is ConfidenceTier.REVIEW_REQUIRED
    assert _classify_tier(0.75) is ConfidenceTier.HIGH
    assert _classify_tier(CONFIDENCE_CAP) is ConfidenceTier.HIGH


def test_missing_supporting_evidence_reduces_confidence() -> None:
    full = _full_candidate()
    without_supporting = IncidentCandidate(
        candidate_id="inc_no_support",
        outlet_id=full.outlet_id,
        incident_type=full.incident_type,
        probable_cause_category=full.probable_cause_category,
        required_signals=full.required_signals,
        supporting_signals=(),
        evidence_event_ids=full.evidence_event_ids,
        window_start=full.window_start,
        window_end=full.window_end,
        correlation_rule_id=full.correlation_rule_id,
        correlation_rule_version=full.correlation_rule_version,
    )

    result = compute_confidence(without_supporting)

    assert result.coverage_component < compute_confidence(full).coverage_component
    assert result.score < compute_confidence(full).score


def test_wider_temporal_spread_reduces_alignment_and_score() -> None:
    compact = _full_candidate()
    spread = IncidentCandidate(
        candidate_id="inc_spread",
        outlet_id=compact.outlet_id,
        incident_type=compact.incident_type,
        probable_cause_category=compact.probable_cause_category,
        required_signals=compact.required_signals,
        supporting_signals=compact.supporting_signals,
        evidence_event_ids=compact.evidence_event_ids,
        window_start=compact.window_start,
        window_end=compact.window_start + timedelta(minutes=60),
        correlation_rule_id=compact.correlation_rule_id,
        correlation_rule_version=compact.correlation_rule_version,
    )

    compact_result = compute_confidence(compact)
    spread_result = compute_confidence(spread)

    assert spread_result.alignment_component == 0.0
    assert spread_result.alignment_component < compact_result.alignment_component
    assert spread_result.score < compact_result.score
