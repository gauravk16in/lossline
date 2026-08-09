"""Point-in-time feature extraction and dataset construction.

This module converts synthetic world outputs (or equivalent structured inputs)
into ``FeatureSnapshot`` rows and ``DatasetRow`` training records while
enforcing point-in-time safety and censored-demand target handling.

Architecture: ``packages/intelligence/`` owns this deterministic domain logic.
The module does not import from the simulator; callers supply typed inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from lossline_intelligence.features.registry import (
    FeatureDataType,
    FeatureDefinition,
    FeatureRegistry,
)
from lossline_intelligence.features.snapshot import (
    PIPELINE_VERSION,
    DatasetRow,
    FeatureSnapshot,
    SnapshotQuality,
    compute_dataset_fingerprint,
    compute_fingerprint,
    compute_snapshot_id,
)

_DP = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Pipeline input types — independent of the simulator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkuFeatureInput:
    """Per-SKU input for feature extraction and target construction."""

    sku_id: str
    base_demand: Decimal
    workload_minutes: Decimal
    opening_inventory: int
    promoted: bool
    promotion_discount: Decimal | None
    # Target / outcome — used for DatasetRow, not model features
    latent_demand: int
    fulfilled: int
    stockout: bool


@dataclass(frozen=True)
class WindowFeatureInput:
    """One service window's complete input for the feature pipeline."""

    outlet_id: str
    service_window: str
    window_start: datetime
    window_end: datetime
    weekday: int
    weather_state: str
    rainfall_mm: Decimal | None
    is_holiday: bool
    local_event: bool
    delivery_share: Decimal
    data_quality: Decimal
    available_capacity_minutes: Decimal
    sku_inputs: tuple[SkuFeatureInput, ...]

    def __post_init__(self) -> None:
        if self.window_start.tzinfo is None or self.window_start.utcoffset() is None:
            raise ValueError("window_start must be timezone-aware")
        if self.window_end.tzinfo is None or self.window_end.utcoffset() is None:
            raise ValueError("window_end must be timezone-aware")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if not self.sku_inputs:
            raise ValueError("at least one SKU input is required")


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


def _validate_feature_type(
    feature_id: str,
    value: bool | int | Decimal | str | None,
    definition: FeatureDefinition,
) -> None:
    """Validate a feature value against its registered data type."""
    if value is None:
        return  # Missing values are tracked separately
    expected = definition.data_type
    if expected is FeatureDataType.BOOLEAN:
        if not isinstance(value, bool):
            raise ValueError(f"{feature_id}: expected bool, got {type(value).__name__}")
    elif expected is FeatureDataType.INTEGER:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{feature_id}: expected int, got {type(value).__name__}")
    elif expected is FeatureDataType.DECIMAL:
        if not isinstance(value, Decimal):
            raise ValueError(f"{feature_id}: expected Decimal, got {type(value).__name__}")
        if not value.is_finite():
            raise ValueError(f"{feature_id}: Decimal value must be finite")
    elif expected is FeatureDataType.CATEGORICAL:
        if not isinstance(value, str):
            raise ValueError(f"{feature_id}: expected str, got {type(value).__name__}")
        if not value.strip():
            raise ValueError(f"{feature_id}: categorical value must be non-empty")


# ---------------------------------------------------------------------------
# Single snapshot builder
# ---------------------------------------------------------------------------


def build_snapshot(
    window: WindowFeatureInput,
    sku: SkuFeatureInput,
    *,
    registry: FeatureRegistry,
    prediction_as_of: datetime,
    pipeline_version: str = PIPELINE_VERSION,
    prior_sku_fulfilled: int | None = None,
    prior_window_end: datetime | None = None,
) -> FeatureSnapshot:
    """Build one ``FeatureSnapshot`` for one outlet × SKU × window.

    Parameters
    ----------
    prior_sku_fulfilled:
        Fulfilled quantity from the immediately preceding window for this SKU.
        ``None`` when no prior data exists.
    prior_window_end:
        End time of the prior window.  Used for future/late-record exclusion:
        the lag feature is only included when the prior window ended before
        ``prediction_as_of``.
    """
    if prediction_as_of.tzinfo is None or prediction_as_of.utcoffset() is None:
        raise ValueError("prediction_as_of must be timezone-aware")
    as_of = prediction_as_of.astimezone(timezone.utc)

    features: dict[str, bool | int | Decimal | str | None] = {}
    missing: list[str] = []
    imputed: list[str] = []

    # --- Context features (future-known / at prediction time) --------------
    features["context.weekday"] = window.weekday
    features["context.service_window"] = window.service_window
    features["context.is_holiday"] = window.is_holiday
    features["context.local_event"] = window.local_event
    features["context.delivery_share"] = window.delivery_share.quantize(
        _DP, rounding=ROUND_HALF_UP
    )
    features["context.data_quality"] = window.data_quality.quantize(
        _DP, rounding=ROUND_HALF_UP
    )

    # --- Weather features (forecast vintage) --------------------------------
    features["weather.state"] = window.weather_state
    if window.rainfall_mm is not None:
        features["weather.rainfall_mm"] = window.rainfall_mm.quantize(
            _DP, rounding=ROUND_HALF_UP
        )
    else:
        features["weather.rainfall_mm"] = None
        missing.append("weather.rainfall_mm")

    # --- Promotion features (per-SKU, scheduled future) --------------------
    features["promotion.active"] = sku.promoted
    if sku.promotion_discount is not None:
        features["promotion.discount_pct"] = sku.promotion_discount.quantize(
            _DP, rounding=ROUND_HALF_UP
        )
    else:
        # Impute to zero when no active promotion (IMPUTE_CONSTANT strategy)
        features["promotion.discount_pct"] = Decimal("0")
        imputed.append("promotion.discount_pct")

    # --- Inventory (per-SKU, observed at prediction time) ------------------
    features["inventory.opening_quantity"] = sku.opening_inventory

    # --- Capacity (outlet-level, observed at prediction time) ---------------
    features["capacity.available_minutes"] = window.available_capacity_minutes.quantize(
        _DP, rounding=ROUND_HALF_UP
    )

    # --- Demand lag feature (historical) -----------------------------------
    # Future/late-record exclusion: only include lag if the prior window
    # ended before prediction_as_of
    lag_available = (
        prior_sku_fulfilled is not None
        and prior_window_end is not None
        and prior_window_end.astimezone(timezone.utc) <= as_of
    )
    if lag_available:
        features["demand.fulfilled_quantity.lag1"] = prior_sku_fulfilled
    else:
        features["demand.fulfilled_quantity.lag1"] = None
        missing.append("demand.fulfilled_quantity.lag1")

    # --- SKU static features -----------------------------------------------
    features["sku.base_demand"] = sku.base_demand.quantize(
        _DP, rounding=ROUND_HALF_UP
    )
    features["sku.workload_minutes"] = sku.workload_minutes.quantize(
        _DP, rounding=ROUND_HALF_UP
    )

    # --- Validate all features against the registry -----------------------
    for feature_id, value in features.items():
        definition = registry.definition_for(feature_id)
        _validate_feature_type(feature_id, value, definition)

    # --- Quality assessment ------------------------------------------------
    total_features = len(features)
    present_count = total_features - len(missing)
    completeness = (Decimal(present_count) / Decimal(total_features)).quantize(
        _DP, rounding=ROUND_HALF_UP
    )

    quality = SnapshotQuality(
        completeness=completeness,
        data_sufficiency=len(missing) == 0,
        stale_feature_ids=(),
        censored_target=sku.stockout,
        data_quality_score=window.data_quality.quantize(_DP, rounding=ROUND_HALF_UP),
    )

    # --- Deterministic identity and fingerprint ----------------------------
    fp = compute_fingerprint(features, pipeline_version, registry.fingerprint)
    sid = compute_snapshot_id(
        window.outlet_id,
        sku.sku_id,
        window.service_window,
        window.window_start,
        as_of,
        pipeline_version,
    )

    now = datetime.now(timezone.utc)

    return FeatureSnapshot(
        snapshot_id=sid,
        pipeline_version=pipeline_version,
        prediction_as_of=as_of,
        outlet_id=window.outlet_id,
        sku_id=sku.sku_id,
        service_window=window.service_window,
        window_start=window.window_start,
        window_end=window.window_end,
        registry_version=registry.registry_version,
        registry_fingerprint=registry.fingerprint,
        feature_values=features,
        source_signal_ids=(),
        missing_features=tuple(sorted(missing)),
        imputed_features=tuple(sorted(imputed)),
        quality=quality,
        fingerprint=fp,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Multi-window dataset builder
# ---------------------------------------------------------------------------


def build_dataset(
    windows: Sequence[WindowFeatureInput],
    *,
    registry: FeatureRegistry,
    prediction_as_of: datetime,
    pipeline_version: str = PIPELINE_VERSION,
) -> tuple[DatasetRow, ...]:
    """Build a training/evaluation dataset from a sequence of windows.

    Windows are processed in order.  Lag features are populated from the
    immediately preceding window for the same outlet × SKU combination.
    Future/late-record exclusion is enforced: lag data from a window that
    ended after ``prediction_as_of`` is not used.

    Each window × SKU produces one ``DatasetRow`` containing the feature
    snapshot and a censored-demand target.
    """
    if prediction_as_of.tzinfo is None or prediction_as_of.utcoffset() is None:
        raise ValueError("prediction_as_of must be timezone-aware")

    rows: list[DatasetRow] = []
    # Track prior state per (outlet, sku)
    prior_fulfilled: dict[tuple[str, str], int] = {}
    prior_end: dict[tuple[str, str], datetime] = {}

    for window in windows:
        for sku in window.sku_inputs:
            key = (window.outlet_id, sku.sku_id)

            snapshot = build_snapshot(
                window,
                sku,
                registry=registry,
                prediction_as_of=prediction_as_of,
                pipeline_version=pipeline_version,
                prior_sku_fulfilled=prior_fulfilled.get(key),
                prior_window_end=prior_end.get(key),
            )

            rows.append(
                DatasetRow(
                    snapshot=snapshot,
                    target_demand_quantity=sku.latent_demand,
                    observed_demand_quantity=sku.fulfilled,
                    censored=sku.stockout,
                )
            )

            # Update lag tracking for the next window
            prior_fulfilled[key] = sku.fulfilled
            prior_end[key] = window.window_end

    return tuple(rows)
