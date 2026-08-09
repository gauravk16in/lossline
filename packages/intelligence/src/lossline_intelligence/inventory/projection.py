"""Inventory projection domain model.

``InventoryProjection`` is an internal frozen dataclass following the C01
``InventoryProjection`` contract.  It stores supply/demand scenario outcomes,
shortage/surplus assessments, and a deterministic identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ShortageSeverity(StrEnum):
    """Projected shortage severity tier."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StockoutTimingMethod(StrEnum):
    CUMULATIVE_CURVE = "CUMULATIVE_CURVE_V1"
    UNIFORM_FALLBACK = "UNIFORM_FALLBACK_V1"


@dataclass(frozen=True)
class InventoryProjection:
    """Immutable inventory projection for one outlet × SKU × service window.

    Follows the C01 ``InventoryProjection`` contract.  This is an internal
    domain object — not a Pydantic serialization boundary.
    """

    projection_id: str
    forecast_id: str
    outlet_id: str
    sku_id: str
    service_window: str
    window_start: datetime
    window_end: datetime

    # Supply inputs
    opening_inventory: int
    replenishment_quantity: int
    usable_supply: int
    safety_buffer: int
    available_for_demand: int

    # Projected ending inventory (from forecast scenarios)
    # "lower" = worst-case inventory (highest demand scenario)
    # "upper" = best-case inventory (lowest demand scenario)
    ending_inventory_point: int
    ending_inventory_lower: int
    ending_inventory_upper: int

    # Shortage (unmet demand after safety buffer)
    shortage_point: int
    shortage_upper: int  # worst-case shortage

    # Surplus (excess above safety buffer after demand)
    surplus_point: int
    surplus_lower: int  # worst-case surplus (highest demand scenario)

    # Risk assessment
    stockout_risk: bool
    shortage_severity: ShortageSeverity
    surplus_risk: bool

    # Stockout-window estimate (fraction of window demand serviceable)
    # None when no stockout is projected.
    stockout_window_fraction: Decimal | None
    stockout_timing_method: StockoutTimingMethod

    # Metadata
    unit: str
    rule_version: str
    evidence_ids: tuple[str, ...]
