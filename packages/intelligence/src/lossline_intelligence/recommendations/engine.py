"""Rule-first recommendation engine for M1 incidents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lossline_intelligence.models.incident import IncidentCandidate, IncidentType
from lossline_intelligence.recommendations.playbooks import (
    CONFIDENCE_THRESHOLD,
    PLAYBOOKS,
    Playbook,
    RiskLevel,
)

SOURCE_RULE = "RULE"


class AbstentionStatus(StrEnum):
    MONITOR_ONLY = "MONITOR_ONLY"
    MANAGER_REVIEW_REQUIRED = "MANAGER_REVIEW_REQUIRED"


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    candidate_id: str
    action_code: str
    action_text: str
    action_steps: tuple[str, ...]
    rationale: str
    urgency: str
    risk_level: RiskLevel
    expected_effect: tuple
    source: str
    rule_id: str
    rule_version: str
    requires_human_approval: bool
    confidence_score: float
    priority_score: float

    @property
    def risk_tier(self) -> RiskLevel:
        """Backward-compatible alias."""
        return self.risk_level


@dataclass(frozen=True)
class RecommendationAbstention:
    candidate_id: str
    status: AbstentionStatus
    reason: str
    confidence_score: float


def _build_recommendation_id(candidate_id: str, playbook: Playbook) -> str:
    return f"rec_{candidate_id}_{playbook.rule_id}_{playbook.rule_version}"


def _priority_score(candidate: IncidentCandidate) -> float:
    if not candidate.signals:
        return 0.0
    return max(sig.severity for sig in candidate.signals)


def recommend(
    candidate: IncidentCandidate,
    confidence: float,
) -> Recommendation | RecommendationAbstention:
    """Return a rule-based recommendation or a deterministic abstention."""
    if confidence < CONFIDENCE_THRESHOLD:
        return RecommendationAbstention(
            candidate_id=candidate.candidate_id,
            status=AbstentionStatus.MONITOR_ONLY,
            reason=(
                f"confidence {confidence:.4f} below threshold "
                f"{CONFIDENCE_THRESHOLD}; no operational recommendation issued"
            ),
            confidence_score=confidence,
        )

    playbook = PLAYBOOKS.get(candidate.probable_cause_category)
    if playbook is None or candidate.incident_type is not IncidentType.OPERATIONAL_OVERLOAD:
        return RecommendationAbstention(
            candidate_id=candidate.candidate_id,
            status=AbstentionStatus.MANAGER_REVIEW_REQUIRED,
            reason="no matching M1 playbook for incident type or cause category",
            confidence_score=confidence,
        )

    priority = _priority_score(candidate)
    return Recommendation(
        recommendation_id=_build_recommendation_id(candidate.candidate_id, playbook),
        candidate_id=candidate.candidate_id,
        action_code=playbook.action_code,
        action_text=playbook.action_steps[0],
        action_steps=playbook.action_steps,
        rationale=playbook.rationale,
        urgency=playbook.urgency.value,
        risk_level=playbook.risk_level,
        expected_effect=playbook.expected_effects,
        source=SOURCE_RULE,
        rule_id=playbook.rule_id,
        rule_version=playbook.rule_version,
        requires_human_approval=True,
        confidence_score=confidence,
        priority_score=priority,
    )


def recommend_action(
    candidate: IncidentCandidate,
    confidence: float,
) -> Recommendation | None:
    """Backward-compatible API — returns None on abstention."""
    result = recommend(candidate, confidence)
    if isinstance(result, RecommendationAbstention):
        return None
    return result
