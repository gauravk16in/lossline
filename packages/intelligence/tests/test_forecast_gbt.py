"""Tests for C06 gradient-boosted tabular forecast model.

Coverage:
  1.  train_requires_minimum_rows — returns None with < min_train_rows uncensored
  2.  artifact_id_is_deterministic — same inputs → same artifact_id/checksum/params_fingerprint
  3.  artifact_stores_training_cutoff — equals max(window_end) of training rows
  4.  artifact_evaluation_metrics_are_finite — MAE, RMSE, WMAPE, bias are finite Decimal
  5.  forecast_produces_valid_bounds — lower ≤ point ≤ upper, all ≥ 0
  6.  forecast_is_repeatable — same artifact + target → identical GBTForecast
  7.  target_window_before_as_of_abstains — GBTAbstention(INVALID_TARGET_SNAPSHOT)
  8.  no_artifact_abstains — forecast_gbt(target, None) → GBTAbstention(NO_ARTIFACT)
  9.  censored_rows_excluded_from_training — censored-only dataset → None from train
  10. gbt_metrics_are_computed_on_test_fold — eval_metrics dict contains mae key
  11. residual_bounds_contain_point — per-row forecasts satisfy lower ≤ point ≤ upper
  12. feature_names_are_deterministic_and_numeric_only — no str features in artifact
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.features import build_demo_registry
from lossline_intelligence.features.pipeline import (
    SkuFeatureInput,
    WindowFeatureInput,
    build_snapshot,
)
from lossline_intelligence.features.snapshot import DatasetRow
from lossline_intelligence.forecasts import (
    GBTAbstention,
    GBTAbstentionReason,
    GBTForecast,
    MLForecastArtifact,
    forecast_gbt,
    train_gbt_model,
)
from lossline_intelligence.forecasts.baseline import (
    evaluate_rolling_baseline,
)


# ---------------------------------------------------------------------------
# Shared helpers (same pattern as test_forecast_baseline.py)
# ---------------------------------------------------------------------------

T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
REGISTRY = build_demo_registry()


def row(
    week: int,
    *,
    demand: int,
    outlet_id: str = "outlet_a",
    sku_id: str = "sku_a",
    censored: bool = False,
    weekday: int = 2,
) -> DatasetRow:
    start = T0 + timedelta(days=7 * week)
    end = start + timedelta(hours=3)
    fulfilled = demand - 2 if censored else demand
    sku = SkuFeatureInput(
        sku_id=sku_id,
        base_demand=Decimal("10"),
        workload_minutes=Decimal("8"),
        opening_inventory=fulfilled,
        promoted=False,
        promotion_discount=None,
        latent_demand=demand,
        fulfilled=fulfilled,
        stockout=censored,
    )
    window = WindowFeatureInput(
        outlet_id=outlet_id,
        service_window="DINNER",
        window_start=start,
        window_end=end,
        weekday=weekday,
        weather_state="CLEAR",
        rainfall_mm=Decimal("0"),
        is_holiday=False,
        local_event=False,
        delivery_share=Decimal("0.4"),
        data_quality=Decimal("1"),
        available_capacity_minutes=Decimal("900"),
        sku_inputs=(sku,),
    )
    snapshot = build_snapshot(
        window,
        sku,
        registry=REGISTRY,
        prediction_as_of=start - timedelta(hours=1),
    )
    return DatasetRow(snapshot, demand, fulfilled, censored)


def history(*demands: int, **kwargs) -> tuple[DatasetRow, ...]:
    return tuple(
        row(index, demand=demand, **kwargs) for index, demand in enumerate(demands)
    )


def big_history(n: int = 30, base: int = 10) -> tuple[DatasetRow, ...]:
    """Generate n rows with linearly increasing demand (good for ML)."""
    return tuple(row(i, demand=base + i) for i in range(n))


# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------


def test_train_requires_minimum_rows() -> None:
    """Returns None when uncensored rows < min_train_rows."""
    small = history(10, 12, 14)  # 3 rows — well below default 20
    result = train_gbt_model(small)
    assert result is None


def test_artifact_id_is_deterministic() -> None:
    """Identical inputs produce identical artifact_id and checksum."""
    rows = big_history(30)
    first = train_gbt_model(rows)
    second = train_gbt_model(rows)

    assert first is not None
    assert second is not None
    assert first.artifact_id == second.artifact_id
    assert first.checksum == second.checksum
    assert first.params_fingerprint == second.params_fingerprint


def test_artifact_stores_training_cutoff() -> None:
    """training_cutoff equals max(window_end) of the training split rows."""
    rows = big_history(30)
    artifact = train_gbt_model(rows, test_fraction=0.2)

    assert artifact is not None
    # Training split = first 80% of 30 rows = 24 rows
    train_split = sorted(rows, key=lambda r: r.snapshot.window_start)[:24]
    expected_cutoff = max(r.snapshot.window_end for r in train_split).astimezone(
        timezone.utc
    )
    assert artifact.training_cutoff == expected_cutoff


def test_artifact_evaluation_metrics_are_finite() -> None:
    """All evaluation metrics are finite Decimal values."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)

    assert artifact is not None
    for key, value in artifact.evaluation_metrics.items():
        assert isinstance(value, Decimal), f"{key} is not Decimal"
        assert value.is_finite(), f"{key} is not finite"


def test_gbt_metrics_are_computed_on_test_fold() -> None:
    """eval_metrics contains 'mae' when test rows exist."""
    rows = big_history(30)
    artifact = train_gbt_model(rows, test_fraction=0.2)

    assert artifact is not None
    assert "mae" in artifact.evaluation_metrics
    assert artifact.evaluation_metrics["mae"] >= Decimal("0")


def test_censored_rows_excluded_from_training() -> None:
    """When all rows are censored, train returns None."""
    all_censored = tuple(row(i, demand=10, censored=True) for i in range(30))
    result = train_gbt_model(all_censored)
    assert result is None


def test_feature_names_are_deterministic_and_numeric_only() -> None:
    """artifact.feature_names must be a sorted tuple of numeric-only features."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)

    assert artifact is not None
    # Must be non-empty
    assert len(artifact.feature_names) > 0
    # Must be a tuple of strings
    assert all(isinstance(n, str) for n in artifact.feature_names)
    # Must be sorted
    assert artifact.feature_names == tuple(sorted(artifact.feature_names))
    # Must not contain string features from the snapshot feature_values
    first_snap = rows[0].snapshot
    for name in artifact.feature_names:
        val = first_snap.feature_values.get(name)
        assert not isinstance(val, str), f"String feature '{name}' in feature_names"


# ---------------------------------------------------------------------------
# Inference tests
# ---------------------------------------------------------------------------


def test_no_artifact_abstains() -> None:
    """forecast_gbt with no artifact returns GBTAbstention(NO_ARTIFACT)."""
    target = row(50, demand=15).snapshot
    result = forecast_gbt(target, None)

    assert isinstance(result, GBTAbstention)
    assert result.reason is GBTAbstentionReason.NO_ARTIFACT
    assert result.feature_snapshot_id == target.snapshot_id
    assert result.artifact_id is None


def test_target_window_before_as_of_abstains() -> None:
    """Returns INVALID_TARGET_SNAPSHOT when window_start < prediction_as_of."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)
    assert artifact is not None

    target = row(50, demand=15).snapshot
    # Pass an as_of after window_start
    as_of = target.window_start + timedelta(seconds=1)
    result = forecast_gbt(target, artifact, prediction_as_of=as_of)

    assert isinstance(result, GBTAbstention)
    assert result.reason is GBTAbstentionReason.INVALID_TARGET_SNAPSHOT


def test_forecast_produces_valid_bounds() -> None:
    """All forecast fields satisfy non-negativity and containment invariants."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)
    assert artifact is not None

    target = row(50, demand=15).snapshot
    result = forecast_gbt(target, artifact)

    assert isinstance(result, GBTForecast)
    assert result.lower_demand >= Decimal("0")
    assert result.point_demand >= Decimal("0")
    assert result.upper_demand >= Decimal("0")
    assert result.lower_demand <= result.point_demand <= result.upper_demand


def test_forecast_is_repeatable() -> None:
    """Same artifact + target always produces the identical GBTForecast."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)
    assert artifact is not None

    target = row(50, demand=15).snapshot
    first = forecast_gbt(target, artifact)
    second = forecast_gbt(target, artifact)

    assert isinstance(first, GBTForecast)
    assert isinstance(second, GBTForecast)
    assert first == second


def test_residual_bounds_contain_point() -> None:
    """Every successful forecast satisfies lower ≤ point ≤ upper."""
    rows = big_history(40)
    artifact = train_gbt_model(rows, test_fraction=0.25)
    assert artifact is not None

    # Forecast on several held-out targets
    for i in range(40, 50):
        target = row(i, demand=10 + i).snapshot
        result = forecast_gbt(target, artifact)
        if isinstance(result, GBTForecast):
            assert result.lower_demand <= result.point_demand, (
                f"lower > point for row {i}"
            )
            assert result.point_demand <= result.upper_demand, (
                f"point > upper for row {i}"
            )


def test_gbt_mae_finite_and_non_negative() -> None:
    """GBT MAE on the test fold is a finite, non-negative Decimal."""
    rows = big_history(30)
    artifact = train_gbt_model(rows)
    assert artifact is not None

    mae = artifact.evaluation_metrics.get("mae")
    assert mae is not None
    assert isinstance(mae, Decimal)
    assert mae.is_finite()
    assert mae >= Decimal("0")
