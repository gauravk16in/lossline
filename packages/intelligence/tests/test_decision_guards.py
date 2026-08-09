from datetime import datetime, timezone
from decimal import Decimal

from lossline_intelligence.decisioning import (
    ActionRisk, DecisionAction, DecisionCandidate, DecisionPolicy,
    GuardDisposition, RiskType, Urgency, guard_decision,
)
from lossline_intelligence.dossiers import (
    ArtifactRef, ConstraintSummary, DataQualitySummary, build_forecast_dossier,
)

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def _dossier():
    ref = lambda i, t: ArtifactRef(artifact_id=i, artifact_type=t, version="v1")
    return build_forecast_dossier(
        outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        prediction_as_of=T0, forecast_refs=(ref("fc1", "forecast"),),
        feature_snapshot_refs=(ref("snap1", "snapshot"),),
        driver_refs=(ref("drv1", "driver"),), data_quality=DataQualitySummary(tier="HIGH"),
        constraints=(ConstraintSummary(constraint_id="con1", constraint_type="STAFFING",
            description="One cook unavailable", evidence_id="staff1"),), provenance_ids=("signal1",),
    )


def _candidate(d=None, **changes):
    d = d or _dossier()
    values = dict(
        decision_id="dec1", decision_version="v1", dossier_id=d.dossier_id,
        forecast_id="fc1", outlet_id="out1", service_window="DINNER",
        window_start=T1, window_end=T2, risk_type=RiskType.INVENTORY_SHORTAGE,
        sku_id="sku1", action=DecisionAction.ADJUST_PREP_QUANTITY,
        quantity=Decimal("10"), unit="portions", execute_by=T1,
        reason_code="SHORTAGE", evidence_ids=("drv1",), urgency=Urgency.HIGH,
        action_risk=ActionRisk.MEDIUM, approval_required=False,
        constraints_considered=("con1",),
    ); values.update(changes); return DecisionCandidate(**values)


def _policy(**changes):
    values = dict(policy_id="policy1", allowed_actions=(DecisionAction.NO_ACTION,
        DecisionAction.ABSTAIN, DecisionAction.ADJUST_PREP_QUANTITY,
        DecisionAction.REALLOCATE_STAFF), max_prep_quantity=Decimal("20"))
    values.update(changes); return DecisionPolicy(**values)


def test_accepts_grounded_in_policy_candidate() -> None:
    d = _dossier(); result = guard_decision(candidate=_candidate(d), dossier=d, policy=_policy())
    assert result.disposition is GuardDisposition.ACCEPT and result.valid


def test_restricts_quantity_down_never_up() -> None:
    d = _dossier(); result = guard_decision(candidate=_candidate(d, quantity=Decimal("23.7")), dossier=d,
        policy=_policy(max_prep_quantity=Decimal("20"), quantity_increment=Decimal("3")))
    assert result.disposition is GuardDisposition.RESTRICT
    assert result.final_decision.quantity == Decimal("18")
    assert result.final_decision.quantity <= Decimal("23.7")


def test_rounding_below_increment_can_reach_zero() -> None:
    d = _dossier(); result = guard_decision(candidate=_candidate(d, quantity=Decimal("0.5")), dossier=d,
        policy=_policy(quantity_increment=Decimal("1")))
    assert result.final_decision.quantity == Decimal("0")


def test_approval_can_only_be_added() -> None:
    d = _dossier(); candidate = _candidate(d, action=DecisionAction.REALLOCATE_STAFF,
        quantity=None, unit=None, approval_required=False)
    result = guard_decision(candidate=candidate, dossier=d, policy=_policy())
    assert result.disposition is GuardDisposition.RESTRICT
    assert result.final_decision.approval_required and result.approval_corrected


def test_scope_and_evidence_mismatches_reject() -> None:
    d = _dossier()
    for candidate, violation in (
        (_candidate(d, outlet_id="other"), "OUTLET_MISMATCH"),
        (_candidate(d, forecast_id="other"), "FORECAST_NOT_IN_DOSSIER"),
        (_candidate(d, evidence_ids=("outside",)), "EVIDENCE_NOT_IN_DOSSIER"),
        (_candidate(d, constraints_considered=("outside",)), "UNKNOWN_CONSTRAINT"),
    ):
        result = guard_decision(candidate=candidate, dossier=d, policy=_policy())
        assert result.disposition is GuardDisposition.REJECT
        assert violation in result.violations and result.final_decision is None


def test_action_unit_and_quantity_policy_rejections() -> None:
    d = _dossier()
    result = guard_decision(candidate=_candidate(d, action=DecisionAction.PAUSE_DELIVERY_SKU,
        quantity=None, unit=None), dossier=d, policy=_policy())
    assert "ACTION_NOT_ALLOWED" in result.violations
    result = guard_decision(candidate=_candidate(d, unit="kg"), dossier=d, policy=_policy())
    assert "PREP_QUANTITY_REQUIRES_PORTIONS" in result.violations


def test_lead_time_boundaries() -> None:
    d = _dossier()
    too_early = T0.replace(minute=10)
    result = guard_decision(candidate=_candidate(d, execute_by=too_early), dossier=d, policy=_policy(min_lead_minutes=15))
    assert "INSUFFICIENT_LEAD_TIME" in result.violations
    result = guard_decision(candidate=_candidate(d, execute_by=T2), dossier=d, policy=_policy())
    assert "EXECUTE_AFTER_WINDOW_START" in result.violations


def test_no_action_and_abstain_are_first_class() -> None:
    d = _dossier()
    no_action = _candidate(d, action=DecisionAction.NO_ACTION, quantity=None, unit=None, sku_id=None)
    assert guard_decision(candidate=no_action, dossier=d, policy=_policy()).disposition is GuardDisposition.ACCEPT
    abstain = no_action.model_copy(update={"action": DecisionAction.ABSTAIN})
    assert guard_decision(candidate=abstain, dossier=d, policy=_policy()).disposition is GuardDisposition.ABSTAIN


def test_invalid_policy_rejects() -> None:
    d = _dossier(); result = guard_decision(candidate=_candidate(d), dossier=d,
        policy=_policy(max_prep_quantity=Decimal("NaN"), quantity_increment=Decimal("0"), min_lead_minutes=-1))
    assert result.disposition is GuardDisposition.REJECT
    assert len(result.violations) == 3


def test_repeatable_guard_identity() -> None:
    d = _dossier(); first = guard_decision(candidate=_candidate(d), dossier=d, policy=_policy())
    second = guard_decision(candidate=_candidate(d), dossier=d, policy=_policy())
    assert first == second
