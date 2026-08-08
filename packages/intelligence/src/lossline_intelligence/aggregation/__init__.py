"""Aggregation sub-package: metric snapshot model and builder."""

from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot
from lossline_intelligence.aggregation.metric_snapshot_builder import (
    NormalizedEvent,
    build_metric_snapshot,
)
from lossline_intelligence.aggregation.baseline import (
    BaselineResult,
    MetricBaseline,
    compute_baseline,
    MIN_HISTORY_WINDOWS,
    BASELINE_VERSION,
)

__all__ = [
    "MetricSnapshot",
    "NormalizedEvent",
    "build_metric_snapshot",
    "BaselineResult",
    "MetricBaseline",
    "compute_baseline",
    "MIN_HISTORY_WINDOWS",
    "BASELINE_VERSION",
]
