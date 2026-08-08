"""Incident domain models used by the correlation and confidence stages.

These are pure value objects — no database, no I/O.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from lossline_intelligence.models.signal import Signal


class IncidentType(StrEnum):
    OPERATIONAL_OVERLOAD = "OPERATIONAL_OVERLOAD"


class ProbableCauseCategory(StrEnum):
    """Deterministic cause category — not free-form LLM prose."""

    OPERATIONAL_CAPACITY_MISMATCH = "OPERATIONAL_CAPACITY_MISMATCH"


@dataclass(frozen=True)
class QualityFlags:
    """Data-quality indicators supplied by the aggregation layer."""

    sample_sufficiency: float = 1.0
    baseline_sufficiency: float = 1.0
    freshness: float = 1.0

    def __post_init__(self) -> None:
        for name in ("sample_sufficiency", "baseline_sufficiency", "freshness"):
            v = getattr(self, name)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"QualityFlags.{name} must be in [0, 1], got {v!r}")


@dataclass(frozen=True)
class IncidentCandidate:
    """Output of the correlation engine — evidence-supported incident hypothesis."""

    candidate_id: str
    outlet_id: str
    incident_type: IncidentType
    probable_cause_category: ProbableCauseCategory
    required_signals: tuple[Signal, ...]
    supporting_signals: tuple[Signal, ...]
    evidence_event_ids: tuple[str, ...]
    window_start: datetime
    window_end: datetime
    correlation_rule_id: str
    correlation_rule_version: str
    quality: QualityFlags = field(default_factory=QualityFlags)

    @property
    def signals(self) -> tuple[Signal, ...]:
        """All correlated signals (required + supporting) for downstream stages."""
        return self.required_signals + self.supporting_signals

    @property
    def restaurant_id(self) -> str:
        """Alias retained for downstream pipeline compatibility."""
        return self.outlet_id

    def __post_init__(self) -> None:
        if not self.required_signals:
            raise ValueError("IncidentCandidate must have at least one required signal")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if len(self.evidence_event_ids) != len(set(self.evidence_event_ids)):
            raise ValueError("evidence_event_ids must be unique")
