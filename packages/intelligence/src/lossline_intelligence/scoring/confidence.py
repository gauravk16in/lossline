"""Deterministic confidence scorer for incident candidates.

Formula (FINAL_IMPLEMENTATION_PLAN.md):
  severity_component       = weighted mean of correlated signal severities
  coverage_component       = present evidence weight / eligible evidence weight
  alignment_component      = max(0, 1 - evidence_span_minutes / SPAN_LIMIT_MINUTES)
  data_quality_component   = mean(sample_sufficiency, baseline_sufficiency, freshness)
  score                    = min(0.95,
                                 0.35 * severity
                               + 0.30 * coverage
                               + 0.20 * alignment
                               + 0.15 * data_quality)

Tier cutoffs (CONFIG_DEFAULT):
  score < 0.50  → MONITOR_ONLY
  0.50 – 0.74   → REVIEW_REQUIRED
  0.75 – 0.95   → HIGH
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lossline_intelligence.models.incident import IncidentCandidate, QualityFlags
from lossline_intelligence.models.signal import SignalType

EVIDENCE_WEIGHTS: dict[SignalType, float] = {
    SignalType.ORDER_VOLUME_SPIKE: 0.20,
    SignalType.PREP_TIME_SPIKE: 0.30,
    SignalType.HANDOFF_DELAY_SPIKE: 0.15,
    SignalType.CANCELLATION_SPIKE: 0.25,
    SignalType.DELAY_REVIEW_SPIKE: 0.10,
}

_W_SEVERITY = 0.35
_W_COVERAGE = 0.30
_W_ALIGNMENT = 0.20
_W_QUALITY = 0.15

SPAN_LIMIT_MINUTES: float = 60.0
CONFIDENCE_CAP: float = 0.95
TIER_REVIEW_THRESHOLD: float = 0.50
TIER_HIGH_THRESHOLD: float = 0.75
FORMULA_VERSION: str = "confidence_v1"


class ConfidenceTier(StrEnum):
    MONITOR_ONLY = "MONITOR_ONLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    tier: ConfidenceTier
    severity_component: float
    coverage_component: float
    alignment_component: float
    data_quality_component: float
    formula_version: str

    @property
    def confidence(self) -> float:
        """Backward-compatible alias for downstream pipeline code."""
        return self.score

    @property
    def data_quality(self) -> float:
        """Backward-compatible alias."""
        return self.data_quality_component


def _classify_tier(score: float) -> ConfidenceTier:
    if score < TIER_REVIEW_THRESHOLD:
        return ConfidenceTier.MONITOR_ONLY
    if score < TIER_HIGH_THRESHOLD:
        return ConfidenceTier.REVIEW_REQUIRED
    return ConfidenceTier.HIGH


def compute_confidence(
    candidate: IncidentCandidate,
    quality: QualityFlags | None = None,
) -> ConfidenceResult:
    """Compute deterministic confidence for an incident candidate."""
    q = quality if quality is not None else candidate.quality

    total_weight = 0.0
    weighted_severity = 0.0
    for sig in candidate.signals:
        w = EVIDENCE_WEIGHTS.get(sig.signal_type, 0.0)
        weighted_severity += sig.severity * w
        total_weight += w
    severity_component = weighted_severity / total_weight if total_weight > 0 else 0.0

    present_types = {sig.signal_type for sig in candidate.signals}
    present_weight = sum(
        EVIDENCE_WEIGHTS.get(t, 0.0) for t in present_types if t in EVIDENCE_WEIGHTS
    )
    total_eligible_weight = sum(EVIDENCE_WEIGHTS.values())
    coverage_component = (
        present_weight / total_eligible_weight if total_eligible_weight > 0 else 0.0
    )

    span_minutes = (
        (candidate.window_end - candidate.window_start).total_seconds() / 60.0
    )
    alignment_component = max(0.0, 1.0 - span_minutes / SPAN_LIMIT_MINUTES)

    data_quality_component = (
        q.sample_sufficiency + q.baseline_sufficiency + q.freshness
    ) / 3.0

    raw = (
        _W_SEVERITY * severity_component
        + _W_COVERAGE * coverage_component
        + _W_ALIGNMENT * alignment_component
        + _W_QUALITY * data_quality_component
    )
    score = min(CONFIDENCE_CAP, raw)

    return ConfidenceResult(
        score=round(score, 6),
        tier=_classify_tier(score),
        severity_component=round(severity_component, 6),
        coverage_component=round(coverage_component, 6),
        alignment_component=round(alignment_component, 6),
        data_quality_component=round(data_quality_component, 6),
        formula_version=FORMULA_VERSION,
    )
