from datetime import datetime, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.decisioning import (
    ActionRisk, DecisionAction, DecisionCandidate, DecisionPolicy, RiskType, Urgency,
)
from lossline_intelligence.dossiers import ArtifactRef, DataQualitySummary, build_forecast_dossier
from src.intelligence.predictive_workflow import (
    SqliteReviewCheckpointStore, resume_manager_review, run_predictive_workflow,
)

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def dossier(outlet="out1"):
    return build_forecast_dossier(
        outlet_id=outlet, service_window="DINNER", window_start=T1, window_end=T2,
        prediction_as_of=T0,
        forecast_refs=(ArtifactRef(artifact_id=f"fc-{outlet}", artifact_type="forecast", version="v1"),),
        feature_snapshot_refs=(ArtifactRef(artifact_id=f"snap-{outlet}", artifact_type="snapshot", version="v1"),),
        data_quality=DataQualitySummary(tier="HIGH"), provenance_ids=("e1",),
    )


class Provider:
    def __init__(self, *, free_form=False): self.calls = 0; self.free_form = free_form
    def propose(self, *, dossier, **kwargs):
        self.calls += 1
        if self.free_form: return "do something"
        item = DecisionCandidate(
            decision_id="dec1", decision_version="v1", dossier_id=dossier.dossier_id,
            forecast_id=dossier.forecast_refs[0].artifact_id, outlet_id=dossier.outlet_id,
            service_window=dossier.service_window, window_start=dossier.window_start,
            window_end=dossier.window_end, risk_type=RiskType.INVENTORY_SHORTAGE,
            sku_id="sku1", action=DecisionAction.ADJUST_PREP_QUANTITY,
            quantity=Decimal("12"), unit="portions", execute_by=dossier.window_start,
            reason_code="SHORTAGE", evidence_ids=("e1",), urgency=Urgency.HIGH,
            action_risk=ActionRisk.MEDIUM, approval_required=True,
        )
        return {"tool_name": "submit_operational_decision", "arguments": item.model_dump(mode="json")}


def policy():
    return DecisionPolicy(policy_id="p1", allowed_actions=(DecisionAction.ADJUST_PREP_QUANTITY,),
        max_prep_quantity=Decimal("10"))


def test_real_nodes_stop_at_durable_review_and_resume_after_reopen(tmp_path) -> None:
    path = tmp_path / "checkpoints.sqlite"; store = SqliteReviewCheckpointStore(path)
    state = run_predictive_workflow(thread_id="t1", dossier=dossier(), provider=Provider(),
        policy=policy(), checkpoint_store=store)
    assert state["status"] == "AWAITING_MANAGER_REVIEW"
    assert state["stages"] == ["load_dossier", "submit_decision", "guard_decision", "manager_review_checkpoint"]
    assert state["guard_result"]["disposition"] == "RESTRICT"
    assert Decimal(state["guard_result"]["final_decision"]["quantity"]) == Decimal("10")
    reopened = SqliteReviewCheckpointStore(path)
    resumed = resume_manager_review(thread_id="t1", manager_decision="APPROVE", checkpoint_store=reopened)
    assert resumed["status"] == "MANAGER_APPROVED"
    assert resumed["stages"][-1] == "manager_review_resumed"


def test_rerun_is_idempotent_and_does_not_call_provider(tmp_path) -> None:
    store = SqliteReviewCheckpointStore(tmp_path / "c.sqlite"); provider = Provider(); d = dossier()
    first = run_predictive_workflow(thread_id="t1", dossier=d, provider=provider, policy=policy(), checkpoint_store=store)
    second = run_predictive_workflow(thread_id="t1", dossier=d, provider=provider, policy=policy(), checkpoint_store=store)
    assert first == second and provider.calls == 1


def test_free_form_abstains_without_review(tmp_path) -> None:
    store = SqliteReviewCheckpointStore(tmp_path / "c.sqlite")
    state = run_predictive_workflow(thread_id="t1", dossier=dossier(), provider=Provider(free_form=True),
        policy=policy(), checkpoint_store=store)
    assert state["status"] == "AGENT_ABSTAINED"
    assert state["stages"][-1] == "finish"
    with pytest.raises(ValueError, match="not awaiting"):
        resume_manager_review(thread_id="t1", manager_decision="APPROVE", checkpoint_store=store)


def test_thread_cannot_be_reused_for_other_dossier(tmp_path) -> None:
    store = SqliteReviewCheckpointStore(tmp_path / "c.sqlite")
    run_predictive_workflow(thread_id="t1", dossier=dossier(), provider=Provider(), policy=policy(), checkpoint_store=store)
    with pytest.raises(ValueError, match="another dossier"):
        run_predictive_workflow(thread_id="t1", dossier=dossier("out2"), provider=Provider(), policy=policy(), checkpoint_store=store)


def test_resume_is_idempotent_but_conflicting_decision_rejected(tmp_path) -> None:
    store = SqliteReviewCheckpointStore(tmp_path / "c.sqlite")
    run_predictive_workflow(thread_id="t1", dossier=dossier(), provider=Provider(), policy=policy(), checkpoint_store=store)
    first = resume_manager_review(thread_id="t1", manager_decision="REJECT", checkpoint_store=store)
    assert resume_manager_review(thread_id="t1", manager_decision="REJECT", checkpoint_store=store) == first
    with pytest.raises(ValueError, match="differently"):
        resume_manager_review(thread_id="t1", manager_decision="APPROVE", checkpoint_store=store)


def test_missing_checkpoint_rejected(tmp_path) -> None:
    store = SqliteReviewCheckpointStore(tmp_path / "c.sqlite")
    with pytest.raises(LookupError, match="not found"):
        resume_manager_review(thread_id="missing", manager_decision="APPROVE", checkpoint_store=store)
