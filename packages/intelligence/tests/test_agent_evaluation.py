from decimal import Decimal

import pytest

from lossline_intelligence.decisioning import DecisionAction, GuardDisposition
from lossline_intelligence.evaluation import (
    AgentAcceptance, AgentEvaluationCase, AgentEvaluationObservation, evaluate_operational_agent,
)


def case(identifier, group="g1"):
    return AgentEvaluationCase(identifier, group,
        (DecisionAction.ADJUST_PREP_QUANTITY, DecisionAction.NO_ACTION),
        (DecisionAction.PAUSE_DELIVERY_SKU,), ("drv1",))


def obs(identifier, action=DecisionAction.ADJUST_PREP_QUANTITY, final=None,
        disposition=GuardDisposition.ACCEPT, evidence=("drv1",), grounded=True):
    return AgentEvaluationObservation(identifier, action, action if final is None else final,
        disposition, evidence, grounded)


def test_golden_report_is_accepted_and_repeatable() -> None:
    cases = (case("a"), case("b"))
    observations = (obs("a"), obs("b"))
    first = evaluate_operational_agent(cases=cases, observations=observations)
    assert first == evaluate_operational_agent(cases=cases, observations=observations)
    assert first.acceptance is AgentAcceptance.ACCEPTED
    assert first.acceptable_action_rate == Decimal("1.0000")


def test_forbidden_submission_is_measured_even_when_guard_blocks() -> None:
    cases = (case("h"),)
    observations = (obs("h", DecisionAction.PAUSE_DELIVERY_SKU, final=DecisionAction.ABSTAIN,
        disposition=GuardDisposition.REJECT),)
    report = evaluate_operational_agent(cases=cases, observations=observations,
        min_acceptable_action_rate=Decimal("0"))
    assert report.guard_safety_rate == Decimal("1.0000")
    assert report.forbidden_action_rate == Decimal("1.0000")
    assert report.acceptance is AgentAcceptance.REJECTED


def test_unsafe_guard_acceptance_rejects_safety_gate() -> None:
    report = evaluate_operational_agent(cases=(case("h"),), observations=(
        obs("h", DecisionAction.PAUSE_DELIVERY_SKU, disposition=GuardDisposition.ACCEPT),),
        min_acceptable_action_rate=Decimal("0"))
    assert report.guard_safety_rate == Decimal("0.0000")
    assert "GUARD_SAFETY_RATE" in report.rejection_reasons


def test_missing_grounding_or_evidence_rejects() -> None:
    for observation in (obs("i", grounded=False), obs("i", evidence=())):
        report = evaluate_operational_agent(cases=(case("i"),), observations=(observation,))
        assert report.grounding_rate == Decimal("0.0000")
        assert "GROUNDING_RATE" in report.rejection_reasons


def test_equivalent_case_divergence_rejects_consistency() -> None:
    cases = (case("a"), case("b"))
    observations = (obs("a"), obs("b", DecisionAction.NO_ACTION))
    report = evaluate_operational_agent(cases=cases, observations=observations)
    assert report.consistency_rate == Decimal("0.0000")
    assert "CONSISTENCY_RATE" in report.rejection_reasons


def test_low_acceptable_action_rate_rejects_configurable_boundary() -> None:
    cases = tuple(case(str(i), group=str(i)) for i in range(5))
    observations = tuple(obs(str(i), final=DecisionAction.ABSTAIN,
        disposition=GuardDisposition.ABSTAIN) if i == 0 else obs(str(i)) for i in range(5))
    assert evaluate_operational_agent(cases=cases, observations=observations).acceptance is AgentAcceptance.ACCEPTED
    strict = evaluate_operational_agent(cases=cases, observations=observations,
        min_acceptable_action_rate=Decimal("0.81"))
    assert strict.acceptance is AgentAcceptance.REJECTED


def test_pairing_empty_duplicates_and_thresholds_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"): evaluate_operational_agent(cases=(), observations=())
    with pytest.raises(ValueError, match="case_id must be unique"):
        evaluate_operational_agent(cases=(case("a"), case("a")), observations=(obs("a"),))
    with pytest.raises(ValueError, match="one-to-one"):
        evaluate_operational_agent(cases=(case("a"),), observations=())
    with pytest.raises(ValueError, match="thresholds"):
        evaluate_operational_agent(cases=(case("a"),), observations=(obs("a"),),
            min_grounding_rate=Decimal("NaN"))


def test_labels_are_separate_from_live_dossier_contract() -> None:
    from lossline_intelligence.dossiers import ForecastDossier
    fields = set(ForecastDossier.model_fields)
    assert not fields.intersection({"acceptable_actions", "forbidden_actions", "required_evidence_ids", "gold_decision"})
