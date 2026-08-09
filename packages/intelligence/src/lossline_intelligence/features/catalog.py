"""Demo feature catalog for golden scenario evaluation.

Defines the initial set of registered features covering context, weather,
promotion, inventory, capacity, demand history and SKU static properties.
"""

from __future__ import annotations

from datetime import timedelta

from lossline_intelligence.features.registry import (
    FeatureAvailability,
    FeatureDataType,
    FeatureDefinition,
    FeatureRegistry,
    FeatureTimeSemantics,
    MissingValueStrategy,
)
from lossline_intelligence.signals.models import SignalCategory

DEMO_REGISTRY_VERSION = "demo.v1"


def _def(
    feature_id: str,
    *,
    source: str,
    category: SignalCategory,
    data_type: FeatureDataType,
    unit: str,
    entity_grain: tuple[str, ...],
    time_semantics: FeatureTimeSemantics,
    availability: FeatureAvailability,
    future_known: bool,
    transformation: str = "identity",
    missing: MissingValueStrategy = MissingValueStrategy.EXPLICIT_MISSING,
    max_staleness: timedelta | None = None,
    leakage: str = "",
) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=feature_id,
        version="v1",
        source=source,
        category=category,
        data_type=data_type,
        unit=unit,
        entity_grain=entity_grain,
        time_semantics=time_semantics,
        availability=availability,
        future_known=future_known,
        transformation=transformation,
        missing_value_strategy=missing,
        max_staleness=max_staleness,
        leakage_rationale=leakage,
    )


DEMO_FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    # --- Calendar / context (future-known) ---------------------------------
    _def(
        "context.weekday",
        source="calendar",
        category=SignalCategory.CALENDAR,
        data_type=FeatureDataType.INTEGER,
        unit="iso_weekday",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.STATIC,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Static calendar attribute; no future information.",
    ),
    _def(
        "context.service_window",
        source="calendar",
        category=SignalCategory.CALENDAR,
        data_type=FeatureDataType.CATEGORICAL,
        unit="window_name",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.STATIC,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Static schedule attribute; no future information.",
    ),
    _def(
        "context.is_holiday",
        source="calendar",
        category=SignalCategory.CALENDAR,
        data_type=FeatureDataType.BOOLEAN,
        unit="flag",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.SCHEDULED_FUTURE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Published holiday schedule known in advance.",
    ),
    _def(
        "context.local_event",
        source="calendar",
        category=SignalCategory.CALENDAR,
        data_type=FeatureDataType.BOOLEAN,
        unit="flag",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.SCHEDULED_FUTURE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Published event schedule known in advance.",
    ),
    _def(
        "context.delivery_share",
        source="operations",
        category=SignalCategory.OPERATIONS,
        data_type=FeatureDataType.DECIMAL,
        unit="ratio",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.OBSERVED,
        availability=FeatureAvailability.AT_PREDICTION_TIME,
        future_known=False,
        leakage="Recent operational observation; safe at prediction time.",
        max_staleness=timedelta(hours=6),
    ),
    _def(
        "context.data_quality",
        source="operations",
        category=SignalCategory.OPERATIONS,
        data_type=FeatureDataType.DECIMAL,
        unit="score",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.OBSERVED,
        availability=FeatureAvailability.AT_PREDICTION_TIME,
        future_known=False,
        leakage="Data completeness at prediction time.",
        max_staleness=timedelta(hours=6),
    ),
    # --- Weather (forecast vintage) ----------------------------------------
    _def(
        "weather.state",
        source="weather_provider",
        category=SignalCategory.WEATHER,
        data_type=FeatureDataType.CATEGORICAL,
        unit="weather_state",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.FORECAST_VINTAGE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Weather forecast vintage published before prediction.",
    ),
    _def(
        "weather.rainfall_mm",
        source="weather_provider",
        category=SignalCategory.WEATHER,
        data_type=FeatureDataType.DECIMAL,
        unit="millimetres",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.FORECAST_VINTAGE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        missing=MissingValueStrategy.EXPLICIT_MISSING,
        leakage="Weather forecast vintage published before prediction.",
    ),
    # --- Promotion (scheduled future) --------------------------------------
    _def(
        "promotion.active",
        source="commercial",
        category=SignalCategory.COMMERCIAL,
        data_type=FeatureDataType.BOOLEAN,
        unit="flag",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.SCHEDULED_FUTURE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Promotion schedule published before prediction.",
    ),
    _def(
        "promotion.discount_pct",
        source="commercial",
        category=SignalCategory.COMMERCIAL,
        data_type=FeatureDataType.DECIMAL,
        unit="ratio",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.SCHEDULED_FUTURE,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        missing=MissingValueStrategy.IMPUTE_CONSTANT,
        leakage="Promotion schedule published before prediction.",
    ),
    # --- Inventory (observed at prediction time) ---------------------------
    _def(
        "inventory.opening_quantity",
        source="inventory_system",
        category=SignalCategory.INVENTORY,
        data_type=FeatureDataType.INTEGER,
        unit="portions",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.OBSERVED,
        availability=FeatureAvailability.AT_PREDICTION_TIME,
        future_known=False,
        leakage="Current inventory snapshot at prediction time.",
        max_staleness=timedelta(hours=1),
    ),
    # --- Capacity (observed at prediction time) ----------------------------
    _def(
        "capacity.available_minutes",
        source="capacity_system",
        category=SignalCategory.CAPACITY,
        data_type=FeatureDataType.DECIMAL,
        unit="minutes",
        entity_grain=("outlet_id",),
        time_semantics=FeatureTimeSemantics.OBSERVED,
        availability=FeatureAvailability.AT_PREDICTION_TIME,
        future_known=False,
        leakage="Current capacity assessment at prediction time.",
        max_staleness=timedelta(hours=1),
    ),
    # --- Demand lag features (historical) ----------------------------------
    _def(
        "demand.fulfilled_quantity.lag1",
        source="demand_history",
        category=SignalCategory.DEMAND,
        data_type=FeatureDataType.INTEGER,
        unit="portions",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.HISTORICAL_LAG,
        availability=FeatureAvailability.AT_PREDICTION_TIME,
        future_known=False,
        missing=MissingValueStrategy.EXPLICIT_MISSING,
        leakage="Prior window fulfilled quantity; known before prediction.",
        max_staleness=timedelta(days=8),
    ),
    # --- SKU static features -----------------------------------------------
    _def(
        "sku.base_demand",
        source="sku_catalog",
        category=SignalCategory.DEMAND,
        data_type=FeatureDataType.DECIMAL,
        unit="portions",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.STATIC,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Static catalog reference; no future information.",
    ),
    _def(
        "sku.workload_minutes",
        source="sku_catalog",
        category=SignalCategory.CAPACITY,
        data_type=FeatureDataType.DECIMAL,
        unit="minutes",
        entity_grain=("outlet_id", "sku_id"),
        time_semantics=FeatureTimeSemantics.STATIC,
        availability=FeatureAvailability.FUTURE_KNOWN,
        future_known=True,
        leakage="Static catalog reference; no future information.",
    ),
)


def build_demo_registry() -> FeatureRegistry:
    """Build the demo feature registry for golden scenario evaluation."""
    return FeatureRegistry(
        DEMO_FEATURE_DEFINITIONS,
        registry_version=DEMO_REGISTRY_VERSION,
    )
