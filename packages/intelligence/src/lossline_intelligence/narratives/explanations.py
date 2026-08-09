"""Grounded structured explanation with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from typing import Annotated

from lossline_intelligence.decisioning import GuardResult
from lossline_intelligence.dossiers import ForecastDossier

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")
_CAUSAL_PATTERNS = (" caused ", " causes ", " will prevent ", " guarantees ", " resulted in ")


class PredictiveExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    headline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    risk_summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    driver_summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    decision_summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    uncertainty_note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    evidence_ids: tuple[Identifier, ...]

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value): raise ValueError("evidence_ids must be unique")
        return value


class ExplanationProvider(Protocol):
    model_name: str
    def generate(self, *, dossier: ForecastDossier, guard_result: GuardResult) -> Any: ...


@dataclass(frozen=True)
class ExplanationGeneration:
    result: PredictiveExplanation
    source: str
    provider_model: str | None
    fallback_reason: str | None


def _allowed_evidence(dossier: ForecastDossier) -> set[str]:
    refs = dossier.forecast_refs + dossier.feature_snapshot_refs + dossier.inventory_refs + dossier.capacity_refs + dossier.risk_refs + dossier.driver_refs + dossier.policy_refs
    return {ref.artifact_id for ref in refs} | set(dossier.provenance_ids) | {c.evidence_id for c in dossier.constraints}


def _allowed_numbers(dossier: ForecastDossier, guard: GuardResult) -> set[Decimal]:
    values: set[Decimal] = set()
    for performance in dossier.historical_performance:
        values.add(performance.mae)
        if performance.wmape is not None: values.add(performance.wmape)
        if performance.interval_coverage is not None: values.add(performance.interval_coverage)
    if guard.final_decision is not None and guard.final_decision.quantity is not None:
        values.add(guard.final_decision.quantity)
    return values


def _validate_grounding(result: PredictiveExplanation, dossier: ForecastDossier, guard: GuardResult) -> None:
    if not set(result.evidence_ids).issubset(_allowed_evidence(dossier)):
        raise ValueError("explanation cites evidence outside dossier")
    text = " ".join((result.headline, result.risk_summary, result.driver_summary,
        result.decision_summary, result.uncertainty_note))
    padded = f" {text.lower()} "
    if any(pattern in padded for pattern in _CAUSAL_PATTERNS):
        raise ValueError("unsupported causal claim")
    allowed = _allowed_numbers(dossier, guard)
    for token in _NUMBER.findall(text):
        is_percent = token.endswith("%")
        number = Decimal(token.rstrip("%"))
        normalized = number / Decimal("100") if is_percent else number
        if not any(normalized == value or number == value for value in allowed):
            raise ValueError("unsupported numeric claim")


def _fallback(dossier: ForecastDossier, guard: GuardResult) -> PredictiveExplanation:
    final = guard.final_decision
    decision = "No guarded operational action is available."
    evidence: tuple[str, ...] = ()
    if final is not None:
        decision = f"The guarded action is {final.action.value.replace('_', ' ').lower()}."
        evidence = final.evidence_ids
    return PredictiveExplanation(
        headline=f"Predictive review for {dossier.service_window.lower()}",
        risk_summary="Computed forecast and projection artifacts require operational review.",
        driver_summary="Only the structured driver evidence in this dossier should be used.",
        decision_summary=decision,
        uncertainty_note="This is evidence-supported association, not proof of causation.",
        evidence_ids=evidence,
    )


def generate_predictive_explanation(
    *, dossier: ForecastDossier, guard_result: GuardResult,
    provider: ExplanationProvider | None = None,
) -> ExplanationGeneration:
    if provider is None:
        return ExplanationGeneration(_fallback(dossier, guard_result), "TEMPLATE", None, "provider_not_configured")
    try:
        result = PredictiveExplanation.model_validate(provider.generate(dossier=dossier, guard_result=guard_result))
        _validate_grounding(result, dossier, guard_result)
        return ExplanationGeneration(result, "LLM", provider.model_name, None)
    except Exception as exc:
        return ExplanationGeneration(_fallback(dossier, guard_result), "TEMPLATE", getattr(provider, "model_name", None), type(exc).__name__)
