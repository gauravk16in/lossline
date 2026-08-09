"""C14 deterministic one-directional decision guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR
from enum import StrEnum
from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict

from lossline_intelligence.decisioning.models import (
    ActionRisk, DecisionAction, DecisionCandidate,
)
from lossline_intelligence.dossiers import ForecastDossier

GUARD_VERSION = "decision_guard.v1"
DEFAULT_QUANTITY_INCREMENT = Decimal("1")
DEFAULT_MIN_LEAD_MINUTES = 15


class GuardDisposition(StrEnum):
    ACCEPT = "ACCEPT"
    RESTRICT = "RESTRICT"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class DecisionPolicy:
    policy_id: str
    allowed_actions: tuple[DecisionAction, ...]
    max_prep_quantity: Decimal
    quantity_increment: Decimal = DEFAULT_QUANTITY_INCREMENT
    min_lead_minutes: int = DEFAULT_MIN_LEAD_MINUTES
    approval_actions: tuple[DecisionAction, ...] = (
        DecisionAction.REALLOCATE_STAFF, DecisionAction.PAUSE_DELIVERY_SKU,
    )


class GuardResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guard_result_id: str
    guard_version: str
    submitted_decision_id: str
    final_decision: DecisionCandidate | None
    valid: bool
    violations: tuple[str, ...]
    restrictions: tuple[str, ...]
    approval_corrected: bool
    unsupported_claims: tuple[str, ...] = ()
    disposition: GuardDisposition


def _allowed_evidence(dossier: ForecastDossier) -> set[str]:
    refs = (
        dossier.forecast_refs + dossier.feature_snapshot_refs + dossier.inventory_refs +
        dossier.capacity_refs + dossier.risk_refs + dossier.driver_refs + dossier.policy_refs
    )
    summary_evidence = tuple(
        evidence for item in dossier.similar_periods + dossier.previous_decisions
        for evidence in item.evidence_ids
    )
    return (
        {item.artifact_id for item in refs} | set(dossier.provenance_ids) |
        set(summary_evidence) | {item.evidence_id for item in dossier.constraints}
    )


def guard_decision(
    *, candidate: DecisionCandidate, dossier: ForecastDossier, policy: DecisionPolicy,
) -> GuardResult:
    """Validate and only restrict a candidate; never broaden its action."""
    violations: list[str] = []
    restrictions: list[str] = []
    if not policy.policy_id.strip(): violations.append("INVALID_POLICY_ID")
    if not policy.max_prep_quantity.is_finite() or policy.max_prep_quantity < 0:
        violations.append("INVALID_POLICY_MAX_QUANTITY")
    if not policy.quantity_increment.is_finite() or policy.quantity_increment <= 0:
        violations.append("INVALID_POLICY_INCREMENT")
    if policy.min_lead_minutes < 0: violations.append("INVALID_POLICY_LEAD_TIME")

    if candidate.dossier_id != dossier.dossier_id: violations.append("DOSSIER_MISMATCH")
    if candidate.outlet_id != dossier.outlet_id: violations.append("OUTLET_MISMATCH")
    if candidate.service_window != dossier.service_window: violations.append("WINDOW_NAME_MISMATCH")
    if candidate.window_start != dossier.window_start or candidate.window_end != dossier.window_end:
        violations.append("WINDOW_BOUNDARY_MISMATCH")
    forecast_ids = {ref.artifact_id for ref in dossier.forecast_refs}
    if candidate.forecast_id not in forecast_ids: violations.append("FORECAST_NOT_IN_DOSSIER")
    allowed_evidence = _allowed_evidence(dossier)
    if not set(candidate.evidence_ids).issubset(allowed_evidence):
        violations.append("EVIDENCE_NOT_IN_DOSSIER")
    constraint_ids = {item.constraint_id for item in dossier.constraints}
    if not set(candidate.constraints_considered).issubset(constraint_ids):
        violations.append("UNKNOWN_CONSTRAINT")
    if candidate.action not in policy.allowed_actions: violations.append("ACTION_NOT_ALLOWED")

    if candidate.execute_by is not None:
        earliest = dossier.prediction_as_of + timedelta(minutes=policy.min_lead_minutes)
        if candidate.execute_by < earliest: violations.append("INSUFFICIENT_LEAD_TIME")
        if candidate.execute_by > dossier.window_start: violations.append("EXECUTE_AFTER_WINDOW_START")

    final = candidate
    if candidate.action is DecisionAction.ADJUST_PREP_QUANTITY:
        if candidate.quantity is None or candidate.unit != "portions":
            violations.append("PREP_QUANTITY_REQUIRES_PORTIONS")
        elif not violations:
            bounded = min(candidate.quantity, policy.max_prep_quantity)
            rounded = (bounded / policy.quantity_increment).to_integral_value(rounding=ROUND_FLOOR) * policy.quantity_increment
            if rounded < candidate.quantity:
                restrictions.append("QUANTITY_REDUCED")
                final = candidate.model_copy(update={"quantity": rounded})
    elif candidate.quantity is not None:
        violations.append("QUANTITY_NOT_ALLOWED_FOR_ACTION")

    approval_required = (
        candidate.approval_required or candidate.action in policy.approval_actions or
        candidate.action_risk is ActionRisk.HIGH
    )
    approval_corrected = approval_required and not candidate.approval_required
    if approval_corrected and not violations:
        restrictions.append("APPROVAL_REQUIRED")
        final = final.model_copy(update={"approval_required": True})

    if candidate.action is DecisionAction.ABSTAIN:
        disposition = GuardDisposition.ABSTAIN
        final = candidate
    elif violations:
        disposition = GuardDisposition.REJECT
        final = None
    elif restrictions:
        disposition = GuardDisposition.RESTRICT
    else:
        disposition = GuardDisposition.ACCEPT

    payload = {
        "candidate": candidate.decision_id, "dossier": dossier.dossier_id,
        "policy": policy.policy_id, "violations": violations, "restrictions": restrictions,
        "final": None if final is None else final.model_dump(mode="json"),
        "version": GUARD_VERSION,
    }
    tag = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return GuardResult(
        guard_result_id=f"grd_{tag}", guard_version=GUARD_VERSION,
        submitted_decision_id=candidate.decision_id, final_decision=final,
        valid=not violations, violations=tuple(violations), restrictions=tuple(restrictions),
        approval_corrected=approval_corrected and not violations, disposition=disposition,
    )
