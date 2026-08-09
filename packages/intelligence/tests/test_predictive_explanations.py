from datetime import datetime, timezone
from decimal import Decimal

from lossline_intelligence.decisioning import (
    ActionRisk, DecisionAction, DecisionCandidate, DecisionPolicy, RiskType, Urgency, guard_decision,
)
from lossline_intelligence.dossiers import (
    ArtifactRef, DataQualitySummary, HistoricalPerformanceSummary, build_forecast_dossier,
)
from lossline_intelligence.narratives import generate_predictive_explanation

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc); T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc); T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def context():
    d = build_forecast_dossier(outlet_id="out1", service_window="DINNER", window_start=T1,
        window_end=T2, prediction_as_of=T0,
        forecast_refs=(ArtifactRef(artifact_id="fc1", artifact_type="forecast", version="v1"),),
        feature_snapshot_refs=(ArtifactRef(artifact_id="snap1", artifact_type="snapshot", version="v1"),),
        driver_refs=(ArtifactRef(artifact_id="drv1", artifact_type="driver", version="v1"),),
        historical_performance=(HistoricalPerformanceSummary(evaluation_id="eval1", sample_count=10,
            mae=Decimal("2.5"), wmape=Decimal("0.1")),), data_quality=DataQualitySummary(tier="HIGH"))
    c = DecisionCandidate(decision_id="dec1", decision_version="v1", dossier_id=d.dossier_id,
        forecast_id="fc1", outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        risk_type=RiskType.INVENTORY_SHORTAGE, sku_id="sku1", action=DecisionAction.ADJUST_PREP_QUANTITY,
        quantity=Decimal("10"), unit="portions", execute_by=T1, reason_code="SHORTAGE",
        evidence_ids=("drv1",), urgency=Urgency.HIGH, action_risk=ActionRisk.MEDIUM,
        approval_required=True)
    g = guard_decision(candidate=c, dossier=d, policy=DecisionPolicy(policy_id="p1",
        allowed_actions=(DecisionAction.ADJUST_PREP_QUANTITY,), max_prep_quantity=Decimal("10")))
    return d, g


class Provider:
    model_name = "fake-model"
    def __init__(self, value): self.value = value
    def generate(self, **kwargs):
        if isinstance(self.value, Exception): raise self.value
        return self.value


def valid(**changes):
    value = dict(headline="Dinner inventory review", risk_summary="A computed shortage risk is present.",
        driver_summary="Registered driver evidence is associated with the forecast.",
        decision_summary="Prepare 10 portions after manager approval.",
        uncertainty_note="This association is not proof of causation.", evidence_ids=("drv1",))
    value.update(changes); return value


def test_valid_grounded_provider_output() -> None:
    d, g = context(); result = generate_predictive_explanation(dossier=d, guard_result=g, provider=Provider(valid()))
    assert result.source == "LLM" and result.provider_model == "fake-model"


def test_missing_provider_uses_deterministic_fallback() -> None:
    d, g = context(); first = generate_predictive_explanation(dossier=d, guard_result=g)
    second = generate_predictive_explanation(dossier=d, guard_result=g)
    assert first == second and first.source == "TEMPLATE"


def test_provider_failure_and_malformed_output_fallback() -> None:
    d, g = context()
    assert generate_predictive_explanation(dossier=d, guard_result=g, provider=Provider(TimeoutError())).fallback_reason == "TimeoutError"
    assert generate_predictive_explanation(dossier=d, guard_result=g, provider=Provider({"headline": "only"})).source == "TEMPLATE"


def test_outside_evidence_falls_back() -> None:
    d, g = context(); result = generate_predictive_explanation(dossier=d, guard_result=g,
        provider=Provider(valid(evidence_ids=("outside",))))
    assert result.source == "TEMPLATE" and result.fallback_reason == "ValueError"


def test_unsupported_number_falls_back_but_grounded_metrics_allowed() -> None:
    d, g = context()
    bad = generate_predictive_explanation(dossier=d, guard_result=g,
        provider=Provider(valid(decision_summary="Prepare 11 portions.")))
    assert bad.source == "TEMPLATE"
    good = generate_predictive_explanation(dossier=d, guard_result=g,
        provider=Provider(valid(risk_summary="Historical WMAPE is 10%.")))
    assert good.source == "LLM"


def test_causal_claims_fall_back() -> None:
    d, g = context()
    for text in ("Rain caused the shortage.", "This will prevent stockouts.", "This guarantees recovery."):
        result = generate_predictive_explanation(dossier=d, guard_result=g,
            provider=Provider(valid(driver_summary=text)))
        assert result.source == "TEMPLATE"


def test_fallback_contains_no_invented_numbers() -> None:
    d, g = context(); result = generate_predictive_explanation(dossier=d, guard_result=g)
    text = " ".join(result.result.model_dump()[key] for key in ("headline", "risk_summary", "driver_summary", "decision_summary", "uncertainty_note"))
    assert "10" not in text and "2.5" not in text
