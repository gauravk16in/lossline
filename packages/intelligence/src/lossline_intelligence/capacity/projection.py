"""Capacity projection domain model.

``CapacityProjection`` is an internal frozen dataclass following the C01
``CapacityProjection`` contract.  It stores SKU workload inputs, station/staff
capacity, utilization scenarios, queue context, and risk tier assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class CapacityRiskTier(StrEnum):
    """Capacity utilization risk tier."""

    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CapacityProjection:
    """Immutable capacity projection for one outlet × service window.

    Follows the C01 ``CapacityProjection`` contract.  SKU workload inputs are
    summarised at the outlet level since capacity is a shared outlet resource.
    """

    projection_id: str
    forecast_id: str
    outlet_id: str
    service_window: str
    window_start: datetime
    window_end: datetime

    # Workload inputs from forecast demand × per-SKU workload_minutes
    demand_workload_point: Decimal      # minutes required for point forecast
    demand_workload_lower: Decimal      # minutes required for lower (min demand)
    demand_workload_upper: Decimal      # minutes required for upper (max demand)

    # Capacity inputs
    available_capacity_minutes: Decimal  # station-minutes available for the window
    effective_capacity_minutes: Decimal  # available × efficiency_factor

    # Utilization (demand_workload / effective_capacity)
    utilization_point: Decimal
    utilization_lower: Decimal
    utilization_upper: Decimal

    # Queue / congestion context
    congestion_factor: Decimal          # max(1, utilization_point)
    mean_preparation_minutes: Decimal   # base_prep × congestion_factor

    # Risk assessment
    risk_tier: CapacityRiskTier
    overloaded: bool                    # utilization_point > 1.0

    # Metadata
    rule_version: str
    evidence_ids: tuple[str, ...]
