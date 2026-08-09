from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lossline_intelligence.decisioning import (
    ActionRisk, AgentAbstention, AgentAbstentionReason, DecisionAction,
    DecisionCandidate, RiskType, Urgency, run_operational_decision,
)
from lossline_intelligence.dossiers import ArtifactRef, DataQualitySummary, build_forecast_dossier
from lossline_intelligence.tools import DossierToolbox

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def dossier():
    ref = lambda i, t: ArtifactRef(artifact_id=i, artifact_type=t, version="v1")
    return build_forecast_dossier(
        outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        prediction_as_of=T0, forecast_refs=(ref("fc1", "forecast"),),
        feature_snapshot_refs=(ref("snap1", "snapshot"),),
        data_quality=DataQualitySummary(tier="HIGH"), provenance_ids=("e1",),
    )


def candidate(**changes):
    values = dict(
        decision_id="dec1", decision_version="v1", dossier_id=dossier().dossier_id,
        forecast_id="fc1", outlet_id="out1", service_window="DINNER",
        window_start=T1, window_end=T2, risk_type=RiskType.INVENTORY_SHORTAGE,
        sku_id="sku1", action=DecisionAction.ADJUST_PREP_QUANTITY,
        quantity=Decimal("10"), unit="portions", execute_by=T1,
        reason_code="SHORTAGE_POINT", evidence_ids=("e1",), urgency=Urgency.HIGH,
        action_risk=ActionRisk.MEDIUM, approval_required=True,
        constraints_considered=("con1",),
    )
    values.update(changes)
    return DecisionCandidate(**values)


class Provider:
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    def propose(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception): raise reply
        return reply


def submission(item=None):
    return {"tool_name": "submit_operational_decision", "arguments": (item or candidate()).model_dump(mode="json")}


def test_valid_terminal_submission() -> None:
    d = dossier(); provider = Provider([submission()])
    result = run_operational_decision(dossier=d, provider=provider, tools=DossierToolbox(d))
    assert isinstance(result, DecisionCandidate)
    assert len(provider.calls) == 1


def test_free_form_cannot_become_decision() -> None:
    d = dossier(); result = run_operational_decision(dossier=d, provider=Provider(["do ten portions"]), tools=DossierToolbox(d))
    assert isinstance(result, AgentAbstention)
    assert result.reason is AgentAbstentionReason.FREE_FORM_COMPLETION


def test_invalid_tool_name_repaired() -> None:
    d = dossier(); provider = Provider([{"tool_name": "other", "arguments": {}}, submission()])
    result = run_operational_decision(dossier=d, provider=provider, tools=DossierToolbox(d))
    assert isinstance(result, DecisionCandidate)
    assert provider.calls[1]["validation_errors"]


def test_repair_limit_exhaustion() -> None:
    d = dossier(); invalid = {"tool_name": "submit_operational_decision", "arguments": {}}
    result = run_operational_decision(dossier=d, provider=Provider([invalid, invalid]), tools=DossierToolbox(d), repair_limit=1)
    assert isinstance(result, AgentAbstention)
    assert result.reason is AgentAbstentionReason.INVALID_SUBMISSION
    assert result.attempts == 2


def test_provider_failure_abstains() -> None:
    d = dossier(); result = run_operational_decision(dossier=d, provider=Provider([RuntimeError("down")]), tools=DossierToolbox(d))
    assert result.reason is AgentAbstentionReason.PROVIDER_FAILURE


def test_toolbox_scope_must_match() -> None:
    first = dossier()
    second = build_forecast_dossier(**({
        "outlet_id": "out2", "service_window": "DINNER", "window_start": T1, "window_end": T2,
        "prediction_as_of": T0, "forecast_refs": (ArtifactRef(artifact_id="fc2", artifact_type="forecast", version="v1"),),
        "feature_snapshot_refs": (ArtifactRef(artifact_id="snap2", artifact_type="snapshot", version="v1"),),
        "data_quality": DataQualitySummary(tier="HIGH")
    }))
    with pytest.raises(ValueError, match="scoped"):
        run_operational_decision(dossier=first, provider=Provider([]), tools=DossierToolbox(second))


def test_quantity_unit_and_no_action_contracts() -> None:
    with pytest.raises(ValidationError, match="supplied together"):
        candidate(unit=None)
    with pytest.raises(ValidationError, match="cannot carry"):
        candidate(action=DecisionAction.NO_ACTION)
    item = candidate(action=DecisionAction.ABSTAIN, quantity=None, unit=None, sku_id=None)
    assert item.quantity is None


def test_non_finite_negative_and_naive_rejected() -> None:
    with pytest.raises(ValidationError, match="finite"):
        candidate(quantity=Decimal("NaN"))
    with pytest.raises(ValidationError, match="non-negative"):
        candidate(quantity=Decimal("-1"))
    with pytest.raises(ValidationError, match="timezone-aware"):
        candidate(window_start=datetime(2026, 1, 7, 13))


def test_candidate_is_strict_frozen() -> None:
    item = candidate()
    with pytest.raises(ValidationError): item.action = DecisionAction.NO_ACTION
    with pytest.raises(ValidationError): DecisionCandidate(**(item.model_dump() | {"extra": True}))


def test_negative_repair_limit_rejected() -> None:
    d = dossier()
    with pytest.raises(ValueError, match="non-negative"):
        run_operational_decision(dossier=d, provider=Provider([]), tools=DossierToolbox(d), repair_limit=-1)
