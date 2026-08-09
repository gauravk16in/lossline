"""Minimal ForecastResult contract for downstream projection consumers (C08/C09).

Person A owns the full forecast pipeline (C05–C07). ``BaselineForecast`` and
``GBTForecast`` in ``lossline_intelligence.forecasts`` are the real
serialization boundaries. This module provides a thin adapter that expresses
the minimal projection-engine contract in terms of C05/C06 field names
(``point_demand``, ``lower_demand``, ``upper_demand``, ``data_sufficient``).

Engine functions (``project_inventory``, ``project_capacity``) accept any
object conforming to this protocol — whether a ``BaselineForecast``, a
``GBTForecast``, or a ``ForecastResult`` stub in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class ForecastLike(Protocol):
    """Structural contract consumed by deterministic projection engines."""

    forecast_id: str
    outlet_id: str
    sku_id: str
    service_window: str
    prediction_as_of: datetime
    window_start: datetime
    window_end: datetime
    point_demand: Decimal
    lower_demand: Decimal
    upper_demand: Decimal
    interval_method: str
    feature_snapshot_id: str
    data_sufficient: bool


@dataclass(frozen=True)
class ForecastResult:
    """Minimal demand forecast stub matching C05/C06 field names.

    Field names deliberately align with ``BaselineForecast`` and
    ``GBTForecast`` so that projection engines work with either.
    Use this class for tests and synthetic scenarios; prefer the real
    ``BaselineForecast`` / ``GBTForecast`` in production code.
    """

    forecast_id: str
    outlet_id: str
    sku_id: str
    service_window: str
    prediction_as_of: datetime
    window_start: datetime
    window_end: datetime
    # Field names match C05 BaselineForecast and C06 GBTForecast
    point_demand: Decimal
    lower_demand: Decimal
    upper_demand: Decimal
    interval_method: str
    model_version: str
    feature_snapshot_id: str
    data_sufficient: bool
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
        for d_name in ("point_demand", "lower_demand", "upper_demand"):
            d = getattr(self, d_name)
            if not d.is_finite():
                raise ValueError(f"{d_name} must be finite")
            if d < 0:
                raise ValueError(f"{d_name} must be non-negative")
        if self.lower_demand > self.point_demand:
            raise ValueError("lower_demand must not exceed point_demand")
        if self.upper_demand < self.point_demand:
            raise ValueError("upper_demand must not be less than point_demand")
