"""Inventory projection model and deterministic projection engine."""

from lossline_intelligence.inventory.projection import (
    InventoryProjection,
    ShortageSeverity,
    StockoutTimingMethod,
)
from lossline_intelligence.inventory.engine import (
    RULE_VERSION,
    project_inventory,
)

__all__ = [
    "RULE_VERSION",
    "InventoryProjection",
    "ShortageSeverity",
    "StockoutTimingMethod",
    "project_inventory",
]
