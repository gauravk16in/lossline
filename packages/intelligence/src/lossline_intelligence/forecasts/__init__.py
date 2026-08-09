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
from lossline_intelligence.forecasts.gbt import (
    GBT_INTERVAL_METHOD,
    GBT_VERSION,
    DEFAULT_PARAMS,
    GBTAbstention,
    GBTAbstentionReason,
    GBTForecast,
    MLForecastArtifact,
    forecast_gbt,
    snapshot_to_feature_vector,
    train_gbt_model,
)

__all__ = [
    # C05 baseline
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
    # C06 GBT
    "GBT_INTERVAL_METHOD",
    "GBT_VERSION",
    "DEFAULT_PARAMS",
    "GBTAbstention",
    "GBTAbstentionReason",
    "GBTForecast",
    "MLForecastArtifact",
    "forecast_gbt",
    "snapshot_to_feature_vector",
    "train_gbt_model",
]
