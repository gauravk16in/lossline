"""Backward-compatible re-export — canonical implementation is in scoring/."""

from lossline_intelligence.scoring.confidence import (
    CONFIDENCE_CAP,
    FORMULA_VERSION as CONFIDENCE_VERSION,
    ConfidenceResult,
    ConfidenceTier,
    compute_confidence,
)

__all__ = [
    "compute_confidence",
    "ConfidenceResult",
    "ConfidenceTier",
    "CONFIDENCE_CAP",
    "CONFIDENCE_VERSION",
]
