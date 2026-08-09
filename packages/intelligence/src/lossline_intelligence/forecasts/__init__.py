"""Demand forecast baselines and model contracts."""

from lossline_intelligence.forecasts.baseline import (
    BASELINE_VERSION,
    INTERVAL_METHOD,
    MIN_HISTORY,
    BaselineAbstention,
    BaselineAbstentionReason,
    BaselineForecast,
    BaselineMetrics,
    BaselineScope,
    evaluate_rolling_baseline,
    forecast_baseline,
)

__all__ = [
    "BASELINE_VERSION",
    "INTERVAL_METHOD",
    "MIN_HISTORY",
    "BaselineAbstention",
    "BaselineAbstentionReason",
    "BaselineForecast",
    "BaselineMetrics",
    "BaselineScope",
    "evaluate_rolling_baseline",
    "forecast_baseline",
]

