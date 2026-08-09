"""Bounded post-detection orchestration for an incident candidate."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.intelligence.explanations import (
    ExplanationEvidence,
    ExplanationProvider,
    generate_explanation,
)

CONFIDENCE_THRESHOLD = 0.50


class InvestigationState(TypedDict):
    candidate_id: str
    outlet_id: str
    incident_type: str
    signals: list[dict[str, Any]]
    confidence: float
    confidence_components: dict[str, float]
    revenue_risk: dict[str, Any]
    recommendation: dict[str, Any] | None
    explanation: dict[str, str] | None
    explanation_source: str | None
    explanation_provider_model: str | None
    explanation_fallback_reason: str | None
    retry_count: int
    stages: list[str]
    status: str


def _with_stage(
    state: InvestigationState, stage: str, **updates: Any
) -> dict[str, Any]:
    return {"stages": [*state["stages"], stage], **updates}


def _load_context(state: InvestigationState) -> dict[str, Any]:
    ExplanationEvidence.model_validate(_explanation_evidence(state))
    return _with_stage(state, "load_context")


def _assess_confidence(state: InvestigationState) -> dict[str, Any]:
    return _with_stage(state, "assess_confidence")


def _route_confidence(
    state: InvestigationState,
) -> Literal["widen_context", "explain"]:
    if state["confidence"] < CONFIDENCE_THRESHOLD and state["retry_count"] == 0:
        return "widen_context"
    return "explain"


def _widen_context(state: InvestigationState) -> dict[str, Any]:
    # The MVP has no additional detector pass here. This records one bounded
    # context-widening request while preserving the deterministic score.
    return _with_stage(state, "widen_context", retry_count=state["retry_count"] + 1)


def _reassess_confidence(state: InvestigationState) -> dict[str, Any]:
    return _with_stage(state, "reassess_confidence")


async def _explain(
    state: InvestigationState, provider: ExplanationProvider | None
) -> dict[str, Any]:
    generated = await generate_explanation(
        ExplanationEvidence.model_validate(_explanation_evidence(state)), provider
    )
    return _with_stage(
        state,
        "explain",
        explanation=generated.result.model_dump(),
        explanation_source=generated.source,
        explanation_provider_model=generated.provider_model,
        explanation_fallback_reason=generated.fallback_reason,
    )


def _recommend(state: InvestigationState) -> dict[str, Any]:
    # Recommendation selection happened deterministically before graph entry.
    return _with_stage(state, "recommend")


def _finalize(state: InvestigationState) -> dict[str, Any]:
    status = (
        "AWAITING_APPROVAL"
        if state["confidence"] >= CONFIDENCE_THRESHOLD
        and state["recommendation"] is not None
        else "MONITOR_ONLY"
    )
    return _with_stage(state, "finalize", status=status)


def _explanation_evidence(state: InvestigationState) -> dict[str, Any]:
    return {
        "incident_type": state["incident_type"],
        "outlet_id": state["outlet_id"],
        "signals": state["signals"],
        "confidence": state["confidence"],
        "confidence_components": state["confidence_components"],
        "revenue_risk": state["revenue_risk"],
        "recommendation": state["recommendation"],
    }


def _build_graph(provider: ExplanationProvider | None = None):
    graph = StateGraph(InvestigationState)
    graph.add_node("load_context", _load_context)
    graph.add_node("assess_confidence", _assess_confidence)
    graph.add_node("widen_context", _widen_context)
    graph.add_node("reassess_confidence", _reassess_confidence)

    async def explain_node(state: InvestigationState) -> dict[str, Any]:
        return await _explain(state, provider)

    graph.add_node("explain", explain_node)
    graph.add_node("recommend", _recommend)
    graph.add_node("finalize", _finalize)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "assess_confidence")
    graph.add_conditional_edges("assess_confidence", _route_confidence)
    graph.add_edge("widen_context", "reassess_confidence")
    graph.add_edge("reassess_confidence", "explain")
    graph.add_edge("explain", "recommend")
    graph.add_edge("recommend", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_investigation(
    *,
    candidate_id: str,
    outlet_id: str,
    incident_type: str,
    signals: list[dict[str, Any]],
    confidence: float,
    confidence_components: dict[str, float],
    revenue_risk: dict[str, Any],
    recommendation: dict[str, Any] | None,
    provider: ExplanationProvider | None = None,
) -> InvestigationState:
    """Orchestrate supplied deterministic results; calculate no business facts."""
    result = await _build_graph(provider).ainvoke(
        {
            "candidate_id": candidate_id,
            "outlet_id": outlet_id,
            "incident_type": incident_type,
            "signals": signals,
            "confidence": confidence,
            "confidence_components": confidence_components,
            "revenue_risk": revenue_risk,
            "recommendation": recommendation,
            "explanation": None,
            "explanation_source": None,
            "explanation_provider_model": None,
            "explanation_fallback_reason": None,
            "retry_count": 0,
            "stages": [],
            "status": "INVESTIGATING",
        }
    )
    return InvestigationState(**result)
