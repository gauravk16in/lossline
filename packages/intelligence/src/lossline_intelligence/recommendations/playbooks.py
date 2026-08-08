"""Versioned M1 playbooks — rule-first, no LLM."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lossline_intelligence.models.incident import ProbableCauseCategory

CONFIDENCE_THRESHOLD: float = 0.50
EXPIRY_MINUTES: int = 15


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Urgency(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ExpectedEffect:
    """Directional expectation for one target metric — not a guaranteed outcome."""

    metric: str
    direction: str
    note: str = ""


@dataclass(frozen=True)
class Playbook:
    rule_id: str
    rule_version: str
    action_code: str
    action_steps: tuple[str, ...]
    rationale: str
    urgency: Urgency
    risk_level: RiskLevel
    expected_effects: tuple[ExpectedEffect, ...]
    expires_after_minutes: int = EXPIRY_MINUTES


OPERATIONAL_OVERLOAD_V1 = Playbook(
    rule_id="OPERATIONAL_OVERLOAD_V1",
    rule_version="recommendation_v1",
    action_code="OPERATIONAL_CAPACITY_RELIEF",
    action_steps=(
        "Temporarily reduce the simulated incoming delivery order load "
        "to relieve kitchen and handoff pressure.",
        "Increase displayed preparation time estimates to manage "
        "customer expectations and reduce complaint volume.",
        "Prioritise the existing simulated queue — focus kitchen "
        "capacity on orders already in progress before accepting new ones.",
    ),
    rationale=(
        "Operational overload pattern: elevated order volume and preparation "
        "time with cancellation impact indicates capacity mismatch during the "
        "lunch-rush window. Advisory steps target simulated load relief only."
    ),
    urgency=Urgency.HIGH,
    risk_level=RiskLevel.MEDIUM,
    expected_effects=(
        ExpectedEffect(
            metric="cancellation_rate",
            direction="decrease",
            note="Target: towards baseline within the next observation window.",
        ),
        ExpectedEffect(
            metric="prep_time_mean_minutes",
            direction="decrease",
            note="Target: towards baseline as load normalises.",
        ),
        ExpectedEffect(
            metric="handoff_wait_mean_minutes",
            direction="decrease",
            note="Expected to follow prep time improvement.",
        ),
    ),
)

PLAYBOOKS: dict[ProbableCauseCategory, Playbook] = {
    ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH: OPERATIONAL_OVERLOAD_V1,
}
