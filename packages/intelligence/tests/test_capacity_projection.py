"""C09 capacity projection tests.

Covers: normal case, overload, utilization scenarios, risk tiers and
boundaries, efficiency factor, multi-SKU workload aggregation, congestion
factor, mean preparation time, deterministic projection ID, input validation,
golden scenario coverage, and separate risk tracking from inventory.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SIMULATOR_ROOT = os.path.join(ROOT, "simulator")
if SIMULATOR_ROOT not in sys.path:
    sys.path.insert(0, SIMULATOR_ROOT)

from lossline_intelligence.capacity import (
    CapacityProjection,
    CapacityRiskTier,
    project_capacity,
)
from lossline_intelligence.capacity.engine import (
    DEFAULT_BASE_PREP_MINUTES,
    DEFAULT_EFFICIENCY_FACTOR,
    RULE_VERSION,
    _compute_risk_tier,
    _safe_utilization,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
_T1 = _T0.replace(hour=16)

# (demand_point, demand_lower, demand_upper, workload_minutes_per_unit)
_SKU_CHICKEN = (Decimal("52"), Decimal("42"), Decimal("65"), Decimal("8"))
_SKU_MUTTON  = (Decimal("28"), Decimal("22"), Decimal("35"), Decimal("10"))
_SKU_ALOO    = (Decimal("20"), Decimal("16"), Decimal("25"), Decimal("6"))

_ALL_SKUS = (_SKU_CHICKEN, _SKU_MUTTON, _SKU_ALOO)


def _proj(
    *,
    sku_workloads=_ALL_SKUS,
    available_capacity_minutes: Decimal = Decimal("900"),
    efficiency_factor: Decimal = DEFAULT_EFFICIENCY_FACTOR,
    base_prep_minutes: Decimal = DEFAULT_BASE_PREP_MINUTES,
    forecast_id: str = "fc_test_001",
) -> CapacityProjection:
    return project_capacity(
        forecast_id=forecast_id,
        outlet_id="meghana_indiranagar",
        service_window="DINNER",
        window_start=_T0,
        window_end=_T1,
        sku_workloads=sku_workloads,
        available_capacity_minutes=available_capacity_minutes,
        efficiency_factor=efficiency_factor,
        base_prep_minutes=base_prep_minutes,
    )


def _expected_workload(demand: Decimal, per_unit: Decimal) -> Decimal:
    return (demand * per_unit).quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Normal case (sufficient capacity)
# ---------------------------------------------------------------------------


class TestNormalCase:
    def test_not_overloaded(self) -> None:
        # 52×8 + 28×10 + 20×6 = 416+280+120 = 816 mins; effective=900×0.85=765
        # util = 816/765 = 1.066 → OVERLOADED
        # Use lower capacity numbers to ensure safe
        p = _proj(
            sku_workloads=((Decimal("30"), Decimal("24"), Decimal("38"), Decimal("8")),),
            available_capacity_minutes=Decimal("500"),
        )
        # 30×8=240; effective=500×0.85=425; util=240/425=0.565 → MODERATE
        assert p.overloaded is False

    def test_projection_is_frozen_dataclass(self) -> None:
        p = _proj()
        with pytest.raises(Exception):
            p.risk_tier = CapacityRiskTier.SAFE  # type: ignore[misc]

    def test_fields_carried(self) -> None:
        p = _proj()
        assert p.outlet_id == "meghana_indiranagar"
        assert p.service_window == "DINNER"
        assert p.forecast_id == "fc_test_001"
        assert p.rule_version == RULE_VERSION


# ---------------------------------------------------------------------------
# Workload aggregation
# ---------------------------------------------------------------------------


class TestWorkloadAggregation:
    def test_single_sku_workload(self) -> None:
        p = _proj(
            sku_workloads=((Decimal("50"), Decimal("40"), Decimal("65"), Decimal("8")),),
            available_capacity_minutes=Decimal("900"),
        )
        assert p.demand_workload_point == Decimal("400.0000")

    def test_multi_sku_workload_point(self) -> None:
        # 52×8=416, 28×10=280, 20×6=120 → 816
        p = _proj()
        assert p.demand_workload_point == Decimal("816.0000")

    def test_multi_sku_workload_lower(self) -> None:
        # 42×8=336, 22×10=220, 16×6=96 → 652
        p = _proj()
        assert p.demand_workload_lower == Decimal("652.0000")

    def test_multi_sku_workload_upper(self) -> None:
        # 65×8=520, 35×10=350, 25×6=150 → 1020
        p = _proj()
        assert p.demand_workload_upper == Decimal("1020.0000")


# ---------------------------------------------------------------------------
# Effective capacity and efficiency factor
# ---------------------------------------------------------------------------


class TestEffectiveCapacity:
    def test_effective_capacity_calculation(self) -> None:
        p = _proj(available_capacity_minutes=Decimal("900"), efficiency_factor=Decimal("0.85"))
        # 900 × 0.85 = 765
        assert p.effective_capacity_minutes == Decimal("765.0000")

    def test_full_efficiency(self) -> None:
        p = _proj(
            sku_workloads=((Decimal("30"), Decimal("24"), Decimal("38"), Decimal("8")),),
            available_capacity_minutes=Decimal("500"),
            efficiency_factor=Decimal("1.0"),
        )
        assert p.effective_capacity_minutes == Decimal("500.0000")

    def test_custom_efficiency(self) -> None:
        p = _proj(
            sku_workloads=((Decimal("30"), Decimal("24"), Decimal("38"), Decimal("8")),),
            available_capacity_minutes=Decimal("500"),
            efficiency_factor=Decimal("0.60"),
        )
        assert p.effective_capacity_minutes == Decimal("300.0000")


# ---------------------------------------------------------------------------
# Utilization scenarios
# ---------------------------------------------------------------------------


class TestUtilization:
    def test_utilization_lower_less_than_point(self) -> None:
        p = _proj()
        assert p.utilization_lower < p.utilization_point

    def test_utilization_upper_greater_than_point(self) -> None:
        p = _proj()
        assert p.utilization_upper > p.utilization_point

    def test_utilization_point_calculation(self) -> None:
        # 816 / 765 = 1.0667
        p = _proj()
        expected = (Decimal("816") / Decimal("765")).quantize(Decimal("0.0001"))
        assert p.utilization_point == expected

    def test_zero_effective_capacity_returns_zero_utilization(self) -> None:
        assert _safe_utilization(Decimal("100"), Decimal("0")) == Decimal("0")

    def test_utilization_quantized(self) -> None:
        p = _proj()
        # Check 4 decimal places
        assert p.utilization_point == p.utilization_point.quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Risk tier
# ---------------------------------------------------------------------------


class TestRiskTier:
    def test_safe_tier(self) -> None:
        # util < 0.70
        assert _compute_risk_tier(Decimal("0.50")) is CapacityRiskTier.SAFE

    def test_moderate_tier(self) -> None:
        # 0.70 ≤ util < 0.90
        assert _compute_risk_tier(Decimal("0.75")) is CapacityRiskTier.MODERATE

    def test_high_tier(self) -> None:
        # 0.90 ≤ util < 1.00
        assert _compute_risk_tier(Decimal("0.95")) is CapacityRiskTier.HIGH

    def test_critical_tier(self) -> None:
        # util ≥ 1.00
        assert _compute_risk_tier(Decimal("1.00")) is CapacityRiskTier.CRITICAL
        assert _compute_risk_tier(Decimal("1.25")) is CapacityRiskTier.CRITICAL

    def test_boundary_safe_moderate(self) -> None:
        assert _compute_risk_tier(Decimal("0.70")) is CapacityRiskTier.MODERATE

    def test_boundary_moderate_high(self) -> None:
        assert _compute_risk_tier(Decimal("0.90")) is CapacityRiskTier.HIGH

    def test_boundary_high_critical(self) -> None:
        assert _compute_risk_tier(Decimal("1.00")) is CapacityRiskTier.CRITICAL

    def test_custom_thresholds(self) -> None:
        p = project_capacity(
            forecast_id="f1", outlet_id="out", service_window="DINNER",
            window_start=_T0, window_end=_T1,
            sku_workloads=((Decimal("80"), Decimal("70"), Decimal("90"), Decimal("1")),),
            available_capacity_minutes=Decimal("100"), efficiency_factor=Decimal("1"),
            moderate_threshold=Decimal("0.50"), high_threshold=Decimal("0.70"),
            critical_threshold=Decimal("0.90"),
        )
        assert p.risk_tier is CapacityRiskTier.HIGH

    def test_invalid_threshold_order_rejected(self) -> None:
        with pytest.raises(ValueError, match="moderate < high < critical"):
            project_capacity(
                forecast_id="f1", outlet_id="out", service_window="DINNER",
                window_start=_T0, window_end=_T1, sku_workloads=_ALL_SKUS,
                available_capacity_minutes=Decimal("900"),
                moderate_threshold=Decimal("0.9"), high_threshold=Decimal("0.8"),
            )


# ---------------------------------------------------------------------------
# Overload
# ---------------------------------------------------------------------------


class TestOverload:
    def test_overloaded_when_utilization_exceeds_one(self) -> None:
        # 816 minutes demand workload, effective=765 → util=1.0667 → overloaded
        p = _proj()
        assert p.overloaded is True

    def test_not_overloaded_sufficient_capacity(self) -> None:
        p = _proj(
            sku_workloads=((Decimal("30"), Decimal("24"), Decimal("38"), Decimal("8")),),
            available_capacity_minutes=Decimal("500"),
        )
        # 240 / 425 = 0.565 → not overloaded
        assert p.overloaded is False

    def test_overloaded_matches_utilization_ge_one(self) -> None:
        p = _proj()
        assert p.overloaded == (p.utilization_point >= Decimal("1"))


# ---------------------------------------------------------------------------
# Congestion and preparation time
# ---------------------------------------------------------------------------


class TestCongestion:
    def test_congestion_at_least_one(self) -> None:
        p = _proj()
        assert p.congestion_factor >= Decimal("1")

    def test_congestion_equals_utilization_when_overloaded(self) -> None:
        p = _proj()
        if p.overloaded:
            assert p.congestion_factor == p.utilization_point

    def test_congestion_one_when_not_overloaded(self) -> None:
        p = _proj(
            sku_workloads=((Decimal("30"), Decimal("24"), Decimal("38"), Decimal("8")),),
            available_capacity_minutes=Decimal("500"),
        )
        if not p.overloaded:
            assert p.congestion_factor == Decimal("1")

    def test_mean_prep_is_base_times_congestion(self) -> None:
        p = _proj()
        expected = (DEFAULT_BASE_PREP_MINUTES * p.congestion_factor).quantize(Decimal("0.0001"))
        assert p.mean_preparation_minutes == expected

    def test_custom_base_prep(self) -> None:
        p = _proj(base_prep_minutes=Decimal("20"))
        assert p.mean_preparation_minutes == (Decimal("20") * p.congestion_factor).quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Deterministic projection ID
# ---------------------------------------------------------------------------


class TestProjectionId:
    def test_same_inputs_same_id(self) -> None:
        p1 = _proj()
        p2 = _proj()
        assert p1.projection_id == p2.projection_id

    def test_different_capacity_different_id(self) -> None:
        p1 = _proj(available_capacity_minutes=Decimal("900"))
        p2 = _proj(available_capacity_minutes=Decimal("850"))
        assert p1.projection_id != p2.projection_id

    def test_id_starts_with_prefix(self) -> None:
        p = _proj()
        assert p.projection_id.startswith("cap_")

    def test_different_efficiency_different_id(self) -> None:
        p1 = _proj(efficiency_factor=Decimal("0.85"))
        p2 = _proj(efficiency_factor=Decimal("0.70"))
        assert p1.projection_id != p2.projection_id


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_zero_capacity_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            project_capacity(
                forecast_id="f1",
                outlet_id="out",
                service_window="DINNER",
                window_start=_T0,
                window_end=_T1,
                sku_workloads=_ALL_SKUS,
                available_capacity_minutes=Decimal("0"),
            )

    def test_negative_capacity_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            project_capacity(
                forecast_id="f1",
                outlet_id="out",
                service_window="DINNER",
                window_start=_T0,
                window_end=_T1,
                sku_workloads=_ALL_SKUS,
                available_capacity_minutes=Decimal("-100"),
            )

    def test_empty_sku_workloads_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one SKU"):
            project_capacity(
                forecast_id="f1",
                outlet_id="out",
                service_window="DINNER",
                window_start=_T0,
                window_end=_T1,
                sku_workloads=(),
                available_capacity_minutes=Decimal("900"),
            )

    def test_efficiency_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="efficiency_factor"):
            _proj(efficiency_factor=Decimal("0"))

    def test_efficiency_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="efficiency_factor"):
            _proj(efficiency_factor=Decimal("1.1"))

    @pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
    def test_non_finite_capacity_rejected(self, value: Decimal) -> None:
        with pytest.raises(ValueError, match="finite Decimal"):
            _proj(available_capacity_minutes=value)

    def test_inverted_demand_bounds_rejected(self) -> None:
        with pytest.raises(ValueError, match="lower <= point <= upper"):
            _proj(sku_workloads=((Decimal("5"), Decimal("6"), Decimal("7"), Decimal("2")),))

    def test_negative_demand_rejected(self) -> None:
        with pytest.raises(ValueError, match="lower <= point <= upper"):
            _proj(sku_workloads=((Decimal("1"), Decimal("-1"), Decimal("2"), Decimal("2")),))

    def test_non_positive_workload_rejected(self) -> None:
        with pytest.raises(ValueError, match="workload_minutes_per_unit"):
            _proj(sku_workloads=((Decimal("1"), Decimal("1"), Decimal("2"), Decimal("0")),))

    def test_naive_window_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            project_capacity(
                forecast_id="f1", outlet_id="out", service_window="DINNER",
                window_start=datetime(2026, 1, 7, 13), window_end=_T1,
                sku_workloads=_ALL_SKUS, available_capacity_minutes=Decimal("900"),
            )

    def test_inverted_window_rejected(self) -> None:
        with pytest.raises(ValueError, match="after window_start"):
            project_capacity(
                forecast_id="f1", outlet_id="out", service_window="DINNER",
                window_start=_T1, window_end=_T0,
                sku_workloads=_ALL_SKUS, available_capacity_minutes=Decimal("900"),
            )

    def test_duplicate_evidence_rejected(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            project_capacity(
                forecast_id="f1", outlet_id="out", service_window="DINNER",
                window_start=_T0, window_end=_T1, sku_workloads=_ALL_SKUS,
                available_capacity_minutes=Decimal("900"), evidence_ids=("e1", "e1"),
            )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_rule_version_carried(self) -> None:
        p = _proj()
        assert p.rule_version == RULE_VERSION

    def test_custom_rule_version(self) -> None:
        p = project_capacity(
            forecast_id="f1",
            outlet_id="out",
            service_window="DINNER",
            window_start=_T0,
            window_end=_T1,
            sku_workloads=_ALL_SKUS,
            available_capacity_minutes=Decimal("900"),
            rule_version="capacity.v2",
        )
        assert p.rule_version == "capacity.v2"

    def test_evidence_ids_stored(self) -> None:
        p = project_capacity(
            forecast_id="f1",
            outlet_id="out",
            service_window="DINNER",
            window_start=_T0,
            window_end=_T1,
            sku_workloads=_ALL_SKUS,
            available_capacity_minutes=Decimal("900"),
            evidence_ids=("sig_001", "sig_002"),
        )
        assert p.evidence_ids == ("sig_001", "sig_002")


# ---------------------------------------------------------------------------
# Separation from inventory risk
# ---------------------------------------------------------------------------


class TestCapacitySeparation:
    def test_capacity_projection_distinct_from_inventory(self) -> None:
        """CapacityProjection is a separate type from InventoryProjection."""
        from lossline_intelligence.inventory import InventoryProjection
        p = _proj()
        assert not isinstance(p, InventoryProjection)
        assert isinstance(p, CapacityProjection)

    def test_no_shortage_fields_on_capacity(self) -> None:
        p = _proj()
        assert not hasattr(p, "shortage_point")
        assert not hasattr(p, "safety_buffer")


# ---------------------------------------------------------------------------
# Golden scenario coverage (via causal world)
# ---------------------------------------------------------------------------


def _from_causal_world():
    try:
        from lossline_simulator.causal_world import (
            GoldenScenario,
            SKU_CONFIGS,
            generate_window,
        )
        return GoldenScenario, SKU_CONFIGS, generate_window
    except ImportError:
        pytest.skip("simulator not installed")


class TestGoldenScenarios:
    def test_scenario_b_friday_surge_overloaded(self) -> None:
        """Scenario B (Friday dinner surge) should produce high/critical utilization."""
        GoldenScenario, SKU_CONFIGS, generate_window = _from_causal_world()
        sw = generate_window(GoldenScenario.FRIDAY_DINNER_SURGE, seed=42, window_start=_T0)
        sku_workloads = tuple(
            (
                so.baseline_demand * so.demand_multiplier,
                so.baseline_demand * so.demand_multiplier * Decimal("0.80"),
                so.baseline_demand * so.demand_multiplier * Decimal("1.25"),
                next(c.workload_minutes for c in SKU_CONFIGS if c.sku_id == so.sku_id),
            )
            for so in sw.sku_outcomes
        )
        p = project_capacity(
            forecast_id="fc_scenario_b",
            outlet_id=sw.outlet_id,
            service_window=sw.context.service_window,
            window_start=sw.window_start,
            window_end=sw.window_end,
            sku_workloads=sku_workloads,
            available_capacity_minutes=sw.available_capacity_minutes,
        )
        assert isinstance(p, CapacityProjection)
        # Friday surge with normal capacity should be elevated
        assert p.risk_tier in (
            CapacityRiskTier.MODERATE,
            CapacityRiskTier.HIGH,
            CapacityRiskTier.CRITICAL,
        )

    def test_scenario_a_normal_weekday_projection(self) -> None:
        GoldenScenario, SKU_CONFIGS, generate_window = _from_causal_world()
        sw = generate_window(GoldenScenario.NORMAL_WEEKDAY, seed=42, window_start=_T0)
        sku_workloads = tuple(
            (
                so.baseline_demand,
                so.baseline_demand * Decimal("0.80"),
                so.baseline_demand * Decimal("1.20"),
                next(c.workload_minutes for c in SKU_CONFIGS if c.sku_id == so.sku_id),
            )
            for so in sw.sku_outcomes
        )
        p = project_capacity(
            forecast_id="fc_scenario_a",
            outlet_id=sw.outlet_id,
            service_window=sw.context.service_window,
            window_start=sw.window_start,
            window_end=sw.window_end,
            sku_workloads=sku_workloads,
            available_capacity_minutes=sw.available_capacity_minutes,
        )
        assert isinstance(p, CapacityProjection)
        assert p.projection_id.startswith("cap_")

    def test_projection_id_deterministic_golden(self) -> None:
        GoldenScenario, SKU_CONFIGS, generate_window = _from_causal_world()
        sw = generate_window(GoldenScenario.NORMAL_WEEKDAY, seed=42, window_start=_T0)
        sku_workloads = tuple(
            (
                so.baseline_demand,
                so.baseline_demand * Decimal("0.80"),
                so.baseline_demand * Decimal("1.20"),
                next(c.workload_minutes for c in SKU_CONFIGS if c.sku_id == so.sku_id),
            )
            for so in sw.sku_outcomes
        )
        kwargs = dict(
            forecast_id="fc_det",
            outlet_id=sw.outlet_id,
            service_window=sw.context.service_window,
            window_start=sw.window_start,
            window_end=sw.window_end,
            sku_workloads=sku_workloads,
            available_capacity_minutes=sw.available_capacity_minutes,
        )
        p1 = project_capacity(**kwargs)
        p2 = project_capacity(**kwargs)
        assert p1.projection_id == p2.projection_id
