"""Backward-compatible re-export — canonical implementation is in scoring/."""

from lossline_intelligence.scoring.revenue_risk import (
    EXPOSURE_LABEL,
    FORECAST_HORIZON_MINUTES,
    FORMULA_VERSION as REVENUE_VERSION,
    RevenueInputs,
    RevenueResult,
    RevenueStatus,
    estimate_revenue_at_risk,
)

__all__ = [
    "estimate_revenue_at_risk",
    "RevenueInputs",
    "RevenueResult",
    "RevenueStatus",
    "REVENUE_VERSION",
    "FORECAST_HORIZON_MINUTES",
    "EXPOSURE_LABEL",
]
