"""Tests for the rule-first recommendation engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.models.incident import (
    IncidentCandidate,
    IncidentType,
    ProbableCauseCategory,
)
from lossline_intelligence.models.signal import Signal, SignalType
from lossline_intelligence.recommendations.engine import (
    AbstentionStatus,
    Recommendation,
    RecommendationAbstention,
    recommend,
    recommend_action,
)
from lossline_intelligence.recommendations.playbooks import (
    CONFIDENCE_THRESHOLD,
    OPERATIONAL_OVERLOAD_V1,
    RiskLevel,
)

_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_W_END = _W_START + timedelta(minutes=30)


def _signal(severity: float = 0.75) -> Signal:
    return Signal.model_validate(
        {
            "signal_id": "sig_test",
            "outlet_id": "store_test",
            "signal_type": SignalType.CANCELLATION_SPIKE,
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


def _overload_candidate(**overrides) -> IncidentCandidate:
    base = {
        "candidate_id": "inc_test",
        "outlet_id": "store_test",
        "incident_type": IncidentType.OPERATIONAL_OVERLOAD,
        "probable_cause_category": ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        "required_signals": (_signal(),),
        "supporting_signals": (),
        "evidence_event_ids": ("evt_001",),
        "window_start": _W_START,
        "window_end": _W_END,
        "correlation_rule_id": "OPERATIONAL_OVERLOAD_V1",
        "correlation_rule_version": "overload_v1",
    }
    base.update(overrides)
    return IncidentCandidate(**base)


def test_known_overload_incident_returns_recommendation() -> None:
    result = recommend(_overload_candidate(), confidence=0.80)
    assert isinstance(result, Recommendation)
    assert result.rule_id == OPERATIONAL_OVERLOAD_V1.rule_id
    assert len(result.action_steps) == 3
    assert result.source == "RULE"
    assert "simulated" in result.action_steps[0].lower()


def test_low_confidence_abstention() -> None:
    result = recommend(_overload_candidate(), confidence=0.49)
    assert isinstance(result, RecommendationAbstention)
    assert result.status is AbstentionStatus.MONITOR_ONLY
    assert recommend_action(_overload_candidate(), confidence=0.49) is None


def test_medium_confidence_returns_recommendation() -> None:
    result = recommend(_overload_candidate(), confidence=0.60)
    assert isinstance(result, Recommendation)
    assert result.confidence_score == 0.60


def test_high_confidence_returns_recommendation() -> None:
    result = recommend(_overload_candidate(), confidence=0.85)
    assert isinstance(result, Recommendation)
    assert result.confidence_score == 0.85


def test_exact_threshold_returns_recommendation() -> None:
    result = recommend(_overload_candidate(), confidence=CONFIDENCE_THRESHOLD)
    assert isinstance(result, Recommendation)


def test_requires_human_approval_always_true() -> None:
    for confidence in (0.55, 0.75, 0.95):
        result = recommend(_overload_candidate(), confidence=confidence)
        assert isinstance(result, Recommendation)
        assert result.requires_human_approval is True


def test_unknown_incident_returns_manager_review_abstention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        __import__(
            "lossline_intelligence.recommendations.playbooks",
            fromlist=["PLAYBOOKS"],
        ).PLAYBOOKS,
        ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        None,  # type: ignore[arg-type]
    )
    # Force lookup miss by clearing the key
    from lossline_intelligence.recommendations import playbooks

    monkeypatch.delitem(
        playbooks.PLAYBOOKS,
        ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH,
        raising=False,
    )
    result = recommend(_overload_candidate(), confidence=0.80)
    assert isinstance(result, RecommendationAbstention)
    assert result.status is AbstentionStatus.MANAGER_REVIEW_REQUIRED


def test_deterministic_recommendation_id() -> None:
    candidate = _overload_candidate()
    r1 = recommend(candidate, confidence=0.80)
    r2 = recommend(candidate, confidence=0.80)
    assert isinstance(r1, Recommendation) and isinstance(r2, Recommendation)
    assert r1.recommendation_id == r2.recommendation_id
    assert candidate.candidate_id in r1.recommendation_id
    assert OPERATIONAL_OVERLOAD_V1.rule_id in r1.recommendation_id


def test_confidence_does_not_alter_risk_level() -> None:
    medium = recommend(_overload_candidate(), confidence=0.60)
    high = recommend(_overload_candidate(), confidence=0.90)
    assert isinstance(medium, Recommendation) and isinstance(high, Recommendation)
    assert medium.risk_level == high.risk_level == RiskLevel.MEDIUM
    assert medium.urgency == high.urgency


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf")])
def test_invalid_confidence_is_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence must be finite"):
        recommend(_overload_candidate(), confidence=confidence)
