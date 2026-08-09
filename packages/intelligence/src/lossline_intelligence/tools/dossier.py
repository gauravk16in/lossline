"""Read-only, allowlisted tools scoped to one immutable dossier."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from lossline_intelligence.dossiers import ArtifactRef, CuratedSummary, ForecastDossier

DEFAULT_READ_BUDGET = 8


class ToolLookupError(LookupError):
    pass


class ToolBudgetExceeded(RuntimeError):
    pass


class ToolResultType(StrEnum):
    ARTIFACT = "ARTIFACT"
    SUMMARY = "SUMMARY"


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    result_type: ToolResultType
    result_id: str
    value: ArtifactRef | CuratedSummary


class DossierToolbox:
    """One-decision read session; callers cannot mutate or enumerate raw stores."""

    def __init__(self, dossier: ForecastDossier, *, read_budget: int = DEFAULT_READ_BUDGET) -> None:
        if read_budget < 0:
            raise ValueError("read_budget must be non-negative")
        refs = tuple(
            ref for collection in (
                dossier.forecast_refs, dossier.feature_snapshot_refs, dossier.inventory_refs,
                dossier.capacity_refs, dossier.risk_refs, dossier.driver_refs, dossier.policy_refs,
            ) for ref in collection
        )
        summaries = dossier.similar_periods + dossier.previous_decisions
        self._dossier_id = dossier.dossier_id
        self._refs: Mapping[str, ArtifactRef] = MappingProxyType({item.artifact_id: item for item in refs})
        self._summaries: Mapping[str, CuratedSummary] = MappingProxyType({item.summary_id: item for item in summaries})
        self._budget = read_budget
        self._reads = 0
        self._trace: list[tuple[str, str]] = []

    @property
    def dossier_id(self) -> str:
        return self._dossier_id

    @property
    def reads_used(self) -> int:
        return self._reads

    @property
    def reads_remaining(self) -> int:
        return self._budget - self._reads

    @property
    def trace(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._trace)

    def _consume(self, tool_name: str, item_id: str) -> None:
        if self._reads >= self._budget:
            raise ToolBudgetExceeded("dossier read-tool budget exhausted")
        self._reads += 1
        self._trace.append((tool_name, item_id))

    def get_artifact_ref(self, artifact_id: str) -> ToolResult:
        self._consume("get_artifact_ref", artifact_id)
        try:
            value = self._refs[artifact_id]
        except KeyError as exc:
            raise ToolLookupError("artifact is not a member of this dossier") from exc
        return ToolResult("get_artifact_ref", ToolResultType.ARTIFACT, artifact_id, value)

    def get_curated_summary(self, summary_id: str) -> ToolResult:
        self._consume("get_curated_summary", summary_id)
        try:
            value = self._summaries[summary_id]
        except KeyError as exc:
            raise ToolLookupError("summary is not a member of this dossier") from exc
        return ToolResult("get_curated_summary", ToolResultType.SUMMARY, summary_id, value)
