"""Seeded causal restaurant world for predictive golden scenarios.

Latent demand is generated before inventory and capacity are applied. Inventory may
censor fulfilled sales; capacity may change preparation time. Neither feeds back into
latent demand within a generated window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
import random
from typing import Mapping


_DP = Decimal("0.0001")
_QUANTITY = Decimal("1")
GENERATOR_VERSION = "causal_world.v1"
OUTLET_ID = "meghana_indiranagar"


class GoldenScenario(StrEnum):
    NORMAL_WEEKDAY = "A_NORMAL_WEEKDAY"
    FRIDAY_DINNER_SURGE = "B_FRIDAY_DINNER_SURGE"
    RAIN_DELIVERY_SURGE = "C_RAIN_DELIVERY_SURGE"
    HOLIDAY_DEMAND_SURGE = "D_HOLIDAY_DEMAND_SURGE"
    PROMOTION_LIMITED_INVENTORY = "E_PROMOTION_LIMITED_INVENTORY"
    WEAK_DEMAND_HIGH_INVENTORY = "F_WEAK_DEMAND_HIGH_INVENTORY"
    MISSING_WEATHER = "G_MISSING_WEATHER"


class WeatherState(StrEnum):
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    MISSING = "MISSING"


@dataclass(frozen=True)
class SkuConfig:
    sku_id: str
    base_demand: Decimal
    workload_minutes: Decimal
    normal_inventory: int


SKU_CONFIGS: tuple[SkuConfig, ...] = (
    SkuConfig("CHICKEN_BIRYANI", Decimal("52"), Decimal("8"), 70),
    SkuConfig("MUTTON_BIRYANI", Decimal("28"), Decimal("10"), 40),
    SkuConfig("ALOO_BIRYANI", Decimal("20"), Decimal("6"), 30),
)


@dataclass(frozen=True)
class SyntheticContext:
    weekday: int
    service_window: str
    weather: WeatherState
    rainfall_mm: Decimal | None
    holiday: bool
    local_event: bool
    promoted_sku_id: str | None
    promotion_discount: Decimal | None
    delivery_share: Decimal
    data_quality: Decimal


@dataclass(frozen=True)
class SyntheticSkuOutcome:
    sku_id: str
    baseline_demand: Decimal
    demand_multiplier: Decimal
    latent_demand_quantity: int
    opening_inventory_quantity: int
    fulfilled_quantity: int
    unfulfilled_quantity: int
    ending_inventory_quantity: int
    stockout: bool
    workload_minutes: Decimal


@dataclass(frozen=True)
class SyntheticWindow:
    generator_version: str
    scenario: GoldenScenario
    seed: int
    outlet_id: str
    window_start: datetime
    window_end: datetime
    context: SyntheticContext
    sku_outcomes: tuple[SyntheticSkuOutcome, ...]
    available_capacity_minutes: Decimal
    total_workload_minutes: Decimal
    capacity_utilization: Decimal
    overloaded: bool
    mean_preparation_minutes: Decimal

    @property
    def latent_demand_quantity(self) -> int:
        return sum(item.latent_demand_quantity for item in self.sku_outcomes)

    @property
    def fulfilled_quantity(self) -> int:
        return sum(item.fulfilled_quantity for item in self.sku_outcomes)


@dataclass(frozen=True)
class _ScenarioParameters:
    weekday: int
    service_window: str
    general_multiplier: Decimal
    weather: WeatherState = WeatherState.CLEAR
    rainfall_mm: Decimal | None = Decimal("0")
    holiday: bool = False
    local_event: bool = False
    promoted_sku_id: str | None = None
    promotion_discount: Decimal | None = None
    delivery_share: Decimal = Decimal("0.40")
    data_quality: Decimal = Decimal("1")
    capacity_minutes: Decimal = Decimal("900")


_PARAMETERS: Mapping[GoldenScenario, _ScenarioParameters] = {
    GoldenScenario.NORMAL_WEEKDAY: _ScenarioParameters(
        weekday=2, service_window="DINNER", general_multiplier=Decimal("1.00")
    ),
    GoldenScenario.FRIDAY_DINNER_SURGE: _ScenarioParameters(
        weekday=4,
        service_window="DINNER",
        general_multiplier=Decimal("1.25"),
        delivery_share=Decimal("0.48"),
        capacity_minutes=Decimal("850"),
    ),
    GoldenScenario.RAIN_DELIVERY_SURGE: _ScenarioParameters(
        weekday=2,
        service_window="DINNER",
        general_multiplier=Decimal("1.12"),
        weather=WeatherState.RAIN,
        rainfall_mm=Decimal("18"),
        delivery_share=Decimal("0.68"),
        capacity_minutes=Decimal("880"),
    ),
    GoldenScenario.HOLIDAY_DEMAND_SURGE: _ScenarioParameters(
        weekday=2,
        service_window="DINNER",
        general_multiplier=Decimal("1.30"),
        holiday=True,
        delivery_share=Decimal("0.52"),
        capacity_minutes=Decimal("1200"),
    ),
    GoldenScenario.PROMOTION_LIMITED_INVENTORY: _ScenarioParameters(
        weekday=2,
        service_window="DINNER",
        general_multiplier=Decimal("1.00"),
        promoted_sku_id="CHICKEN_BIRYANI",
        promotion_discount=Decimal("0.20"),
        delivery_share=Decimal("0.50"),
        capacity_minutes=Decimal("1000"),
    ),
    GoldenScenario.WEAK_DEMAND_HIGH_INVENTORY: _ScenarioParameters(
        weekday=1,
        service_window="DINNER",
        general_multiplier=Decimal("0.62"),
        delivery_share=Decimal("0.30"),
        capacity_minutes=Decimal("1100"),
    ),
    GoldenScenario.MISSING_WEATHER: _ScenarioParameters(
        weekday=2,
        service_window="DINNER",
        general_multiplier=Decimal("1.00"),
        weather=WeatherState.MISSING,
        rainfall_mm=None,
        data_quality=Decimal("0.75"),
    ),
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("window_start must include a UTC offset")
    return value.astimezone(timezone.utc)


def _scenario_seed(seed: int, scenario: GoldenScenario) -> int:
    stable_tag = sum((index + 1) * ord(char) for index, char in enumerate(scenario.value))
    return seed * 100_003 + stable_tag


def _multiplier(config: SkuConfig, parameters: _ScenarioParameters) -> Decimal:
    result = parameters.general_multiplier
    if parameters.promoted_sku_id == config.sku_id:
        result *= Decimal("1.35")
    if parameters.local_event:
        result *= Decimal("1.10")
    return result.quantize(_DP, rounding=ROUND_HALF_UP)


def _latent_demand(
    config: SkuConfig,
    parameters: _ScenarioParameters,
    rng: random.Random,
) -> tuple[Decimal, int]:
    multiplier = _multiplier(config, parameters)
    noise = Decimal(str(rng.uniform(-0.025, 0.025)))
    expected = config.base_demand * multiplier * (Decimal("1") + noise)
    quantity = int(expected.quantize(_QUANTITY, rounding=ROUND_HALF_UP))
    return multiplier, max(0, quantity)


def generate_window(
    scenario: GoldenScenario,
    *,
    seed: int,
    window_start: datetime,
    inventory_overrides: Mapping[str, int] | None = None,
    capacity_override: Decimal | None = None,
) -> SyntheticWindow:
    """Generate one deterministic outcome while preserving causal separation."""

    start = _utc(window_start)
    parameters = _PARAMETERS[scenario]
    rng = random.Random(_scenario_seed(seed, scenario))
    inventory = dict(inventory_overrides or {})
    known_skus = {item.sku_id for item in SKU_CONFIGS}
    unknown_skus = sorted(set(inventory) - known_skus)
    if unknown_skus:
        raise ValueError(f"unknown inventory SKU IDs: {unknown_skus}")
    if any(value < 0 for value in inventory.values()):
        raise ValueError("inventory overrides cannot be negative")

    capacity = parameters.capacity_minutes if capacity_override is None else capacity_override
    if not capacity.is_finite() or capacity <= 0:
        raise ValueError("capacity must be finite and positive")

    outcomes: list[SyntheticSkuOutcome] = []
    for config in SKU_CONFIGS:
        multiplier, latent = _latent_demand(config, parameters, rng)
        default_inventory = config.normal_inventory
        if scenario is GoldenScenario.PROMOTION_LIMITED_INVENTORY and config.sku_id == "CHICKEN_BIRYANI":
            default_inventory = 45
        elif scenario is GoldenScenario.WEAK_DEMAND_HIGH_INVENTORY:
            default_inventory = config.normal_inventory * 2
        opening = inventory.get(config.sku_id, default_inventory)
        fulfilled = min(latent, opening)
        unfulfilled = latent - fulfilled
        ending = opening - fulfilled
        workload = (Decimal(latent) * config.workload_minutes).quantize(
            _DP, rounding=ROUND_HALF_UP
        )
        outcomes.append(
            SyntheticSkuOutcome(
                sku_id=config.sku_id,
                baseline_demand=config.base_demand,
                demand_multiplier=multiplier,
                latent_demand_quantity=latent,
                opening_inventory_quantity=opening,
                fulfilled_quantity=fulfilled,
                unfulfilled_quantity=unfulfilled,
                ending_inventory_quantity=ending,
                stockout=unfulfilled > 0,
                workload_minutes=workload,
            )
        )

    total_workload = sum(
        (item.workload_minutes for item in outcomes), Decimal("0")
    ).quantize(_DP, rounding=ROUND_HALF_UP)
    utilization = (total_workload / capacity).quantize(_DP, rounding=ROUND_HALF_UP)
    congestion = max(Decimal("1"), utilization)
    mean_prep = (Decimal("15") * congestion).quantize(_DP, rounding=ROUND_HALF_UP)

    return SyntheticWindow(
        generator_version=GENERATOR_VERSION,
        scenario=scenario,
        seed=seed,
        outlet_id=OUTLET_ID,
        window_start=start,
        window_end=start + timedelta(hours=3),
        context=SyntheticContext(
            weekday=parameters.weekday,
            service_window=parameters.service_window,
            weather=parameters.weather,
            rainfall_mm=parameters.rainfall_mm,
            holiday=parameters.holiday,
            local_event=parameters.local_event,
            promoted_sku_id=parameters.promoted_sku_id,
            promotion_discount=parameters.promotion_discount,
            delivery_share=parameters.delivery_share,
            data_quality=parameters.data_quality,
        ),
        sku_outcomes=tuple(outcomes),
        available_capacity_minutes=capacity.quantize(_DP, rounding=ROUND_HALF_UP),
        total_workload_minutes=total_workload,
        capacity_utilization=utilization,
        overloaded=total_workload > capacity,
        mean_preparation_minutes=mean_prep,
    )


def generate_golden_scenarios(
    *, seed: int, window_start: datetime
) -> tuple[SyntheticWindow, ...]:
    """Generate scenarios A–G in stable enum order."""

    return tuple(
        generate_window(scenario, seed=seed, window_start=window_start)
        for scenario in GoldenScenario
    )
