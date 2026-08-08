"""Pipeline modules: correlation, confidence, revenue, recommendations, outcome."""

from lossline_intelligence.pipelines.confidence import ConfidenceResult, compute_confidence
from lossline_intelligence.pipelines.correlation import correlate_overload
from lossline_intelligence.pipelines.outcome import (
    OutcomeClassification,
    OutcomeResult,
    WindowMetrics,
    classify_outcome,
)
from lossline_intelligence.pipelines.recommendations import Recommendation, recommend_action
from lossline_intelligence.pipelines.revenue import RevenueInputs, RevenueResult, estimate_revenue_at_risk

__all__ = [
    "correlate_overload",
    "ConfidenceResult", "compute_confidence",
    "RevenueInputs", "RevenueResult", "estimate_revenue_at_risk",
    "Recommendation", "recommend_action",
    "OutcomeClassification", "OutcomeResult", "WindowMetrics", "classify_outcome",
]
