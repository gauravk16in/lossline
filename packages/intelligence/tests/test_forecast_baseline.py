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
    BaselineAbstention,
    BaselineAbstentionReason,
    BaselineForecast,
    BaselineScope,
    evaluate_rolling_baseline,
    forecast_baseline,
)


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


def test_comparable_median_and_empirical_bounds_are_repeatable() -> None:
    rows = history(10, 12, 14, 20)
    target = row(4, demand=99).snapshot

    first = forecast_baseline(target, rows, prediction_as_of=target.window_start)
    second = forecast_baseline(target, rows, prediction_as_of=target.window_start)

    assert isinstance(first, BaselineForecast)
    assert first == second
    assert first.point_demand == Decimal("13.0000")
    assert first.lower_demand == Decimal("10.6000")
    assert first.upper_demand == Decimal("18.2000")
    assert first.scope is BaselineScope.OUTLET_SKU_WEEKDAY_WINDOW
    assert first.sample_count == 4


def test_at_threshold_history_forecasts_and_below_threshold_abstains() -> None:
    target = row(4, demand=99).snapshot
    assert isinstance(
        forecast_baseline(
            target, history(10, 11, 12, 13), prediction_as_of=target.window_start
        ),
        BaselineForecast,
    )
    result = forecast_baseline(
        target, history(10, 11, 12), prediction_as_of=target.window_start
    )
    assert isinstance(result, BaselineAbstention)
    assert result.reason is BaselineAbstentionReason.INSUFFICIENT_UNCENSORED_HISTORY


def test_censored_history_is_excluded() -> None:
    rows = (*history(10, 11, 12), row(3, demand=50, censored=True))
    target = row(4, demand=99).snapshot

    result = forecast_baseline(target, rows, prediction_as_of=target.window_start)

    assert isinstance(result, BaselineAbstention)
    assert result.available_uncensored_history == 3


def test_records_after_prediction_time_are_excluded() -> None:
    rows = history(10, 11, 12, 13)
    target = row(6, demand=99).snapshot
    as_of = T0 - timedelta(minutes=1)

    result = forecast_baseline(target, rows, prediction_as_of=as_of)

    assert isinstance(result, BaselineAbstention)
    assert result.available_uncensored_history == 0


def test_sku_scope_backoff_uses_other_outlets() -> None:
    rows = history(10, 12, 14, 16, outlet_id="outlet_b")
    target = row(4, demand=99, outlet_id="outlet_a").snapshot

    result = forecast_baseline(target, rows, prediction_as_of=target.window_start)

    assert isinstance(result, BaselineForecast)
    assert result.scope is BaselineScope.SKU_WEEKDAY_WINDOW


def test_category_scope_backoff_requires_explicit_catalog_mapping() -> None:
    rows = history(10, 12, 14, 16, sku_id="sku_b")
    target = row(4, demand=99, sku_id="sku_a").snapshot

    result = forecast_baseline(
        target,
        rows,
        prediction_as_of=target.window_start,
        sku_categories={"sku_a": "BIRYANI", "sku_b": "BIRYANI"},
    )

    assert isinstance(result, BaselineForecast)
    assert result.scope is BaselineScope.OUTLET_CATEGORY_WEEKDAY_WINDOW


def test_global_weekday_backoff_without_category() -> None:
    rows = history(10, 12, 14, 16, outlet_id="outlet_b", sku_id="sku_b")
    target = row(4, demand=99, outlet_id="outlet_a", sku_id="sku_a").snapshot

    result = forecast_baseline(target, rows, prediction_as_of=target.window_start)

    assert isinstance(result, BaselineForecast)
    assert result.scope is BaselineScope.GLOBAL_WEEKDAY_WINDOW


def test_global_backoff_handles_different_weekday() -> None:
    rows = history(
        10, 12, 14, 16, outlet_id="outlet_b", sku_id="sku_b", weekday=1
    )
    target = row(4, demand=99, outlet_id="outlet_a", sku_id="sku_a").snapshot

    result = forecast_baseline(target, rows, prediction_as_of=target.window_start)

    assert isinstance(result, BaselineForecast)
    assert result.scope is BaselineScope.GLOBAL


def test_target_window_before_as_of_abstains() -> None:
    target = row(4, demand=99).snapshot
    result = forecast_baseline(
        target,
        history(10, 11, 12, 13),
        prediction_as_of=target.window_start + timedelta(seconds=1),
    )

    assert isinstance(result, BaselineAbstention)
    assert result.reason is BaselineAbstentionReason.INVALID_TARGET_SNAPSHOT


def test_rolling_evaluation_calculates_required_metrics() -> None:
    metrics = evaluate_rolling_baseline(history(10, 12, 14, 16, 18, 20))

    assert metrics.forecast_count == 2
    assert metrics.abstention_count == 4
    assert metrics.mae == Decimal("5.5000")
    assert metrics.rmse == Decimal("5.5227")
    assert metrics.wmape == Decimal("0.2895")
    assert metrics.bias == Decimal("-5.5000")


def test_zero_actual_wmape_is_explicitly_unavailable() -> None:
    metrics = evaluate_rolling_baseline(history(0, 0, 0, 0, 0))

    assert metrics.forecast_count == 1
    assert metrics.wmape is None
    assert metrics.mae == Decimal("0.0000")


def test_invalid_min_history_and_naive_as_of_rejected() -> None:
    target = row(4, demand=99).snapshot
    with pytest.raises(ValueError, match="positive"):
        forecast_baseline(
            target, (), prediction_as_of=target.window_start, min_history=0
        )
    with pytest.raises(ValueError, match="UTC offset"):
        forecast_baseline(
            target,
            (),
            prediction_as_of=target.window_start.replace(tzinfo=None),
        )

