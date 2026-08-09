"""C13 provider-agnostic bounded submission loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from pydantic import ValidationError

from lossline_intelligence.decisioning.models import DecisionCandidate, DecisionSubmission
from lossline_intelligence.dossiers import ForecastDossier
from lossline_intelligence.tools import DossierToolbox

DEFAULT_REPAIR_LIMIT = 2


class AgentAbstentionReason(StrEnum):
    FREE_FORM_COMPLETION = "FREE_FORM_COMPLETION"
    INVALID_SUBMISSION = "INVALID_SUBMISSION"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


@dataclass(frozen=True)
class AgentAbstention:
    dossier_id: str
    reason: AgentAbstentionReason
    attempts: int
    validation_errors: tuple[str, ...]


class OperationalDecisionProvider(Protocol):
    def propose(
        self, *, dossier: ForecastDossier, tools: DossierToolbox,
        attempt: int, validation_errors: tuple[str, ...],
    ) -> Any: ...


def run_operational_decision(
    *, dossier: ForecastDossier, provider: OperationalDecisionProvider,
    tools: DossierToolbox, repair_limit: int = DEFAULT_REPAIR_LIMIT,
) -> DecisionCandidate | AgentAbstention:
    """Accept only the terminal submission tool; retry schema failures finitely."""
    if tools.dossier_id != dossier.dossier_id:
        raise ValueError("toolbox must be scoped to the supplied dossier")
    if repair_limit < 0:
        raise ValueError("repair_limit must be non-negative")
    errors: tuple[str, ...] = ()
    for attempt in range(1, repair_limit + 2):
        try:
            raw = provider.propose(dossier=dossier, tools=tools, attempt=attempt, validation_errors=errors)
        except Exception as exc:
            return AgentAbstention(dossier.dossier_id, AgentAbstentionReason.PROVIDER_FAILURE, attempt, (type(exc).__name__,))
        if isinstance(raw, str):
            return AgentAbstention(dossier.dossier_id, AgentAbstentionReason.FREE_FORM_COMPLETION, attempt, ())
        try:
            submission = DecisionSubmission.model_validate(raw)
        except ValidationError as exc:
            errors = tuple(error["msg"] for error in exc.errors())
            continue
        return submission.arguments
    return AgentAbstention(dossier.dossier_id, AgentAbstentionReason.INVALID_SUBMISSION, repair_limit + 1, errors)
