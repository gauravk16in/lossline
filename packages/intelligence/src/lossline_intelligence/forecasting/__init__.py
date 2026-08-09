"""Minimal ForecastResult contract for downstream projection consumers.

Person A owns the full forecast pipeline (C05–C07).  This module defines
the minimal typed contract that C08/C09 projection engines require.
Person A's implementation will produce objects conforming to this shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import StringConstraints

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


@dataclass(frozen=True)
class ForecastResult:
    """Immutable demand forecast for one outlet × SKU × service window.

    This is an internal domain object (not a serialization boundary).
    """

    forecast_id: str
    outlet_id: str
    sku_id: str
    service_window: str
    prediction_as_of: datetime
    window_start: datetime
    window_end: datetime
    demand_point: Decimal
    demand_lower: Decimal
    demand_upper: Decimal
    interval_method: str
    model_version: str
    feature_snapshot_id: str
    data_sufficiency: bool
    quality_flags: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "forecast_id",
            "outlet_id",
            "sku_id",
            "service_window",
            "interval_method",
            "model_version",
            "feature_snapshot_id",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        for ts_name in ("prediction_as_of", "window_start", "window_end"):
            ts = getattr(self, ts_name)
            if ts.tzinfo is None or ts.utcoffset() is None:
                raise ValueError(f"{ts_name} must be timezone-aware")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        for d_name in ("demand_point", "demand_lower", "demand_upper"):
            d = getattr(self, d_name)
            if not d.is_finite():
                raise ValueError(f"{d_name} must be finite")
            if d < 0:
                raise ValueError(f"{d_name} must be non-negative")
        if self.demand_lower > self.demand_point:
            raise ValueError("demand_lower must not exceed demand_point")
        if self.demand_upper < self.demand_point:
            raise ValueError("demand_upper must not be less than demand_point")
