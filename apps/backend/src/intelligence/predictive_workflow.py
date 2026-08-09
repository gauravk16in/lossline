"""C16 predictive artifact workflow with durable manager-review checkpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from lossline_intelligence.decisioning import (
    AgentAbstention, DecisionCandidate, DecisionPolicy, GuardDisposition,
    OperationalDecisionProvider, guard_decision, run_operational_decision,
)
from lossline_intelligence.dossiers import ForecastDossier
from lossline_intelligence.tools import DossierToolbox

WORKFLOW_VERSION = "predictive_workflow.v1"


class PredictiveWorkflowState(TypedDict):
    thread_id: str
    workflow_version: str
    dossier_id: str
    stages: list[str]
    status: str
    submitted_decision: dict[str, Any] | None
    agent_abstention: dict[str, Any] | None
    guard_result: dict[str, Any] | None
    manager_decision: str | None


class SqliteReviewCheckpointStore:
    """Small durable store; a new process can reopen and resume a review."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS predictive_checkpoints ("
                "thread_id TEXT PRIMARY KEY, workflow_version TEXT NOT NULL, "
                "status TEXT NOT NULL, state_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )

    def save(self, state: PredictiveWorkflowState) -> None:
        encoded = json.dumps(state, sort_keys=True, separators=(",", ":"))
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO predictive_checkpoints VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET workflow_version=excluded.workflow_version, "
                "status=excluded.status, state_json=excluded.state_json, updated_at=excluded.updated_at",
                (state["thread_id"], state["workflow_version"], state["status"], encoded,
                 datetime.now(timezone.utc).isoformat()),
            )

    def load(self, thread_id: str) -> PredictiveWorkflowState | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT state_json FROM predictive_checkpoints WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return None if row is None else PredictiveWorkflowState(**json.loads(row[0]))


def _persisted(state: PredictiveWorkflowState, store: SqliteReviewCheckpointStore,
               stage: str, **updates: Any) -> dict[str, Any]:
    merged = PredictiveWorkflowState(**{**state, "stages": [*state["stages"], stage], **updates})
    store.save(merged)
    return {"stages": merged["stages"], **updates}


def run_predictive_workflow(
    *, thread_id: str, dossier: ForecastDossier, provider: OperationalDecisionProvider,
    policy: DecisionPolicy, checkpoint_store: SqliteReviewCheckpointStore,
    read_budget: int = 8, repair_limit: int = 2,
) -> PredictiveWorkflowState:
    """Run real decision and guard nodes, stopping durably for manager review."""
    existing = checkpoint_store.load(thread_id)
    if existing is not None:
        if existing["dossier_id"] != dossier.dossier_id:
            raise ValueError("thread_id already belongs to another dossier")
        return existing

    graph = StateGraph(PredictiveWorkflowState)

    def load_context(state: PredictiveWorkflowState) -> dict[str, Any]:
        return _persisted(state, checkpoint_store, "load_dossier", status="DOSSIER_LOADED")

    def decide(state: PredictiveWorkflowState) -> dict[str, Any]:
        result = run_operational_decision(
            dossier=dossier, provider=provider, tools=DossierToolbox(dossier, read_budget=read_budget),
            repair_limit=repair_limit,
        )
        if isinstance(result, AgentAbstention):
            abstention = {
                "dossier_id": result.dossier_id, "reason": result.reason.value,
                "attempts": result.attempts, "validation_errors": list(result.validation_errors),
            }
            return _persisted(state, checkpoint_store, "submit_decision", status="AGENT_ABSTAINED",
                agent_abstention=abstention)
        return _persisted(state, checkpoint_store, "submit_decision", status="DECISION_SUBMITTED",
            submitted_decision=result.model_dump(mode="json"))

    def route_after_decision(state: PredictiveWorkflowState) -> Literal["guard", "finish"]:
        return "finish" if state["agent_abstention"] is not None else "guard"

    def guard(state: PredictiveWorkflowState) -> dict[str, Any]:
        candidate = DecisionCandidate.model_validate(state["submitted_decision"])
        result = guard_decision(candidate=candidate, dossier=dossier, policy=policy)
        terminal = result.disposition in (GuardDisposition.REJECT, GuardDisposition.ABSTAIN)
        return _persisted(state, checkpoint_store, "guard_decision",
            status="GUARD_TERMINAL" if terminal else "GUARDED", guard_result=result.model_dump(mode="json"))

    def route_after_guard(state: PredictiveWorkflowState) -> Literal["review", "finish"]:
        return "finish" if state["status"] == "GUARD_TERMINAL" else "review"

    def review(state: PredictiveWorkflowState) -> dict[str, Any]:
        return _persisted(state, checkpoint_store, "manager_review_checkpoint",
            status="AWAITING_MANAGER_REVIEW")

    def finish(state: PredictiveWorkflowState) -> dict[str, Any]:
        return _persisted(state, checkpoint_store, "finish", status=state["status"])

    graph.add_node("load", load_context); graph.add_node("decide", decide)
    graph.add_node("guard", guard); graph.add_node("review", review); graph.add_node("finish", finish)
    graph.add_edge(START, "load"); graph.add_edge("load", "decide")
    graph.add_conditional_edges("decide", route_after_decision, {"guard": "guard", "finish": "finish"})
    graph.add_conditional_edges("guard", route_after_guard, {"review": "review", "finish": "finish"})
    graph.add_edge("review", END); graph.add_edge("finish", END)
    compiled = graph.compile()
    initial = PredictiveWorkflowState(
        thread_id=thread_id, workflow_version=WORKFLOW_VERSION, dossier_id=dossier.dossier_id,
        stages=[], status="STARTED", submitted_decision=None, agent_abstention=None,
        guard_result=None, manager_decision=None,
    )
    checkpoint_store.save(initial)
    return PredictiveWorkflowState(**compiled.invoke(initial))


def resume_manager_review(
    *, thread_id: str, manager_decision: Literal["APPROVE", "REJECT"],
    checkpoint_store: SqliteReviewCheckpointStore,
) -> PredictiveWorkflowState:
    state = checkpoint_store.load(thread_id)
    if state is None: raise LookupError("predictive checkpoint not found")
    if state["status"] in {"MANAGER_APPROVED", "MANAGER_REJECTED"}:
        expected = "MANAGER_APPROVED" if manager_decision == "APPROVE" else "MANAGER_REJECTED"
        if state["status"] != expected: raise ValueError("manager review already finalized differently")
        return state
    if state["status"] != "AWAITING_MANAGER_REVIEW":
        raise ValueError("workflow is not awaiting manager review")
    status = "MANAGER_APPROVED" if manager_decision == "APPROVE" else "MANAGER_REJECTED"
    resumed = PredictiveWorkflowState(**{**state, "status": status,
        "manager_decision": manager_decision, "stages": [*state["stages"], "manager_review_resumed"]})
    checkpoint_store.save(resumed)
    return resumed
