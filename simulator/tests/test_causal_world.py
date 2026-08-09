from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "simulator"))

from lossline_simulator.causal_world import (  # noqa: E402
    GoldenScenario,
    WeatherState,
    generate_golden_scenarios,
    generate_window,
)


START = datetime(2026, 8, 14, 12, 30, tzinfo=timezone.utc)
SEED = 42


def _sku(window, sku_id: str):
    return next(item for item in window.sku_outcomes if item.sku_id == sku_id)


def test_generation_is_repeatable_and_seed_sensitive() -> None:
    left = generate_golden_scenarios(seed=SEED, window_start=START)
    right = generate_golden_scenarios(seed=SEED, window_start=START)
    changed = generate_golden_scenarios(seed=SEED + 1, window_start=START)

    assert left == right
    assert [item.latent_demand_quantity for item in left] != [
        item.latent_demand_quantity for item in changed
    ]
    assert len(left) == 7


def test_inventory_censors_sales_without_changing_latent_demand() -> None:
    scarce = generate_window(
        GoldenScenario.NORMAL_WEEKDAY,
        seed=SEED,
        window_start=START,
        inventory_overrides={"CHICKEN_BIRYANI": 1},
    )
    abundant = generate_window(
        GoldenScenario.NORMAL_WEEKDAY,
        seed=SEED,
        window_start=START,
        inventory_overrides={"CHICKEN_BIRYANI": 1_000},
    )

    scarce_sku = _sku(scarce, "CHICKEN_BIRYANI")
    abundant_sku = _sku(abundant, "CHICKEN_BIRYANI")
    assert scarce_sku.latent_demand_quantity == abundant_sku.latent_demand_quantity
    assert scarce_sku.fulfilled_quantity == 1
    assert scarce_sku.unfulfilled_quantity > 0
    assert abundant_sku.unfulfilled_quantity == 0


def test_capacity_changes_prep_outcome_not_demand() -> None:
    constrained = generate_window(
        GoldenScenario.NORMAL_WEEKDAY,
        seed=SEED,
        window_start=START,
        capacity_override=Decimal("400"),
    )
    ample = generate_window(
        GoldenScenario.NORMAL_WEEKDAY,
        seed=SEED,
        window_start=START,
        capacity_override=Decimal("2000"),
    )

    assert constrained.latent_demand_quantity == ample.latent_demand_quantity
    assert constrained.mean_preparation_minutes > ample.mean_preparation_minutes
    assert constrained.overloaded is True
    assert ample.overloaded is False


def test_normal_weekday_has_no_action_conditions() -> None:
    window = generate_window(
        GoldenScenario.NORMAL_WEEKDAY, seed=SEED, window_start=START
    )

    assert window.overloaded is False
    assert not any(item.stockout for item in window.sku_outcomes)


def test_friday_dinner_creates_capacity_warning() -> None:
    normal = generate_window(
        GoldenScenario.NORMAL_WEEKDAY, seed=SEED, window_start=START
    )
    friday = generate_window(
        GoldenScenario.FRIDAY_DINNER_SURGE, seed=SEED, window_start=START
    )

    assert friday.latent_demand_quantity > normal.latent_demand_quantity
    assert friday.overloaded is True


def test_rain_increases_delivery_demand_and_can_overload() -> None:
    normal = generate_window(
        GoldenScenario.NORMAL_WEEKDAY, seed=SEED, window_start=START
    )
    rain = generate_window(
        GoldenScenario.RAIN_DELIVERY_SURGE, seed=SEED, window_start=START
    )

    assert rain.context.weather is WeatherState.RAIN
    assert rain.context.delivery_share > normal.context.delivery_share
    assert rain.latent_demand_quantity > normal.latent_demand_quantity
    assert rain.overloaded is True


def test_holiday_increases_sku_demand_without_forcing_stockout() -> None:
    normal = generate_window(
        GoldenScenario.NORMAL_WEEKDAY, seed=SEED, window_start=START
    )
    holiday = generate_window(
        GoldenScenario.HOLIDAY_DEMAND_SURGE, seed=SEED, window_start=START
    )

    assert holiday.context.holiday is True
    assert _sku(holiday, "CHICKEN_BIRYANI").latent_demand_quantity > _sku(
        normal, "CHICKEN_BIRYANI"
    ).latent_demand_quantity


def test_promotion_targets_sku_and_limited_inventory_stockouts() -> None:
    window = generate_window(
        GoldenScenario.PROMOTION_LIMITED_INVENTORY,
        seed=SEED,
        window_start=START,
    )
    chicken = _sku(window, "CHICKEN_BIRYANI")
    mutton = _sku(window, "MUTTON_BIRYANI")

    assert window.context.promoted_sku_id == chicken.sku_id
    assert window.context.weekday == 5
    assert window.context.weather is WeatherState.RAIN
    assert window.context.rainfall_mm == Decimal("18")
    assert chicken.demand_multiplier > mutton.demand_multiplier
    assert chicken.stockout is True


def test_weak_demand_leaves_surplus_inventory() -> None:
    window = generate_window(
        GoldenScenario.WEAK_DEMAND_HIGH_INVENTORY,
        seed=SEED,
        window_start=START,
    )

    assert window.overloaded is False
    assert all(item.ending_inventory_quantity > 0 for item in window.sku_outcomes)
    assert not any(item.stockout for item in window.sku_outcomes)


def test_missing_weather_reduces_quality_without_stopping_generation() -> None:
    window = generate_window(
        GoldenScenario.MISSING_WEATHER, seed=SEED, window_start=START
    )

    assert window.context.weather is WeatherState.MISSING
    assert window.context.rainfall_mm is None
    assert window.context.data_quality < Decimal("1")
    assert window.latent_demand_quantity > 0


def test_rejects_naive_time_negative_inventory_and_invalid_capacity() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        generate_window(
            GoldenScenario.NORMAL_WEEKDAY,
            seed=SEED,
            window_start=START.replace(tzinfo=None),
        )
    with pytest.raises(ValueError, match="inventory"):
        generate_window(
            GoldenScenario.NORMAL_WEEKDAY,
            seed=SEED,
            window_start=START,
            inventory_overrides={"CHICKEN_BIRYANI": -1},
        )
    with pytest.raises(ValueError, match="unknown inventory SKU"):
        generate_window(
            GoldenScenario.NORMAL_WEEKDAY,
            seed=SEED,
            window_start=START,
            inventory_overrides={"UNKNOWN": 1},
        )
    with pytest.raises(ValueError, match="capacity"):
        generate_window(
            GoldenScenario.NORMAL_WEEKDAY,
            seed=SEED,
            window_start=START,
            capacity_override=Decimal("NaN"),
        )
