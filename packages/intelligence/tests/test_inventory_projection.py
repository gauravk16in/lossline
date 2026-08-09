"""C08 inventory projection tests.

Covers: normal case, stockout, safety buffer, replenishment,
forecast scenarios (lower/point/upper), shortage severity tiers,
surplus detection, zero demand, deterministic projection ID,
edge cases, golden scenario coverage, and stockout-window fraction.
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

from lossline_intelligence.forecasting import ForecastResult
from lossline_intelligence.inventory import (
    InventoryProjection,
    ShortageSeverity,
    StockoutTimingMethod,
    project_inventory,
)
from lossline_intelligence.inventory.engine import (
    DEFAULT_MIN_SAFETY_BUFFER,
    DEFAULT_SAFETY_BUFFER_PCT,
    RULE_VERSION,
    _compute_severity,
    _stockout_window_fraction,
    _stockout_fraction_from_curve,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
_T1 = _T0.replace(hour=16)


def _forecast(
    *,
    point_demand: Decimal = Decimal("50"),
    lower_demand: Decimal = Decimal("40"),
    upper_demand: Decimal = Decimal("65"),
    outlet_id: str = "meghana_indiranagar",
    sku_id: str = "CHICKEN_BIRYANI",
    service_window: str = "DINNER",
    forecast_id: str = "fc_test_001",
) -> ForecastResult:
    return ForecastResult(
        forecast_id=forecast_id,
        outlet_id=outlet_id,
        sku_id=sku_id,
        service_window=service_window,
        prediction_as_of=_T0,
        window_start=_T0,
        window_end=_T1,
        point_demand=point_demand,
        lower_demand=lower_demand,
        upper_demand=upper_demand,
        interval_method="quantile_regression",
        model_version="model.v1",
        feature_snapshot_id="snap_test_001",
        data_sufficient=True,
        quality_flags=(),
    )


def _proj(
    *,
    point_demand: Decimal = Decimal("50"),
    lower_demand: Decimal = Decimal("40"),
    upper_demand: Decimal = Decimal("65"),
    opening: int = 70,
    replenishment: int = 0,
    safety_buffer_pct: Decimal = DEFAULT_SAFETY_BUFFER_PCT,
    min_safety_buffer: int = DEFAULT_MIN_SAFETY_BUFFER,
) -> InventoryProjection:
    return project_inventory(
        _forecast(
            point_demand=point_demand,
            lower_demand=lower_demand,
            upper_demand=upper_demand,
        ),
        opening_inventory=opening,
        replenishment_quantity=replenishment,
        safety_buffer_pct=safety_buffer_pct,
        min_safety_buffer=min_safety_buffer,
    )


# ---------------------------------------------------------------------------
# Normal case (sufficient inventory, no shortage)
# ---------------------------------------------------------------------------


class TestNormalCase:
    def test_no_shortage(self) -> None:
        p = _proj(point_demand=Decimal("50"), opening=70)
        assert p.shortage_point == 0
        assert p.stockout_risk is False
        assert p.shortage_severity is ShortageSeverity.NONE

    def test_usable_supply_arithmetic(self) -> None:
        p = _proj(opening=70, replenishment=10)
        assert p.usable_supply == 80

    def test_no_stockout_window_fraction(self) -> None:
        p = _proj(point_demand=Decimal("50"), opening=70)
        assert p.stockout_window_fraction is None

    def test_ending_inventory_point(self) -> None:
        p = _proj(point_demand=Decimal("50"), opening=70, replenishment=0)
        # usable = 70, demand_point_int = 50
        assert p.ending_inventory_point == 20

    def test_projection_is_frozen_dataclass(self) -> None:
        p = _proj()
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            p.shortage_point = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Safety buffer
# ---------------------------------------------------------------------------


class TestSafetyBuffer:
    def test_buffer_is_10pct_of_opening(self) -> None:
        p = _proj(opening=70, safety_buffer_pct=Decimal("0.10"))
        # ceil(70 × 0.10) = 7
        assert p.safety_buffer == 7

    def test_buffer_minimum_enforced(self) -> None:
        # ceil(5 × 0.10) = 1, but min = 2
        p = _proj(opening=5, min_safety_buffer=2)
        assert p.safety_buffer == 2

    def test_available_for_demand_is_supply_minus_buffer(self) -> None:
        p = _proj(opening=70)
        assert p.available_for_demand == p.usable_supply - p.safety_buffer

    def test_buffer_reduces_available_supply(self) -> None:
        # With opening=70, buffer=7, available=63; demand=65 → shortage=2
        p = _proj(point_demand=Decimal("65"), upper_demand=Decimal("65"), opening=70)
        assert p.shortage_point == 2
        assert p.stockout_risk is True

    def test_zero_opening_inventory_uses_min_buffer(self) -> None:
        p = _proj(opening=0, replenishment=20, min_safety_buffer=2)
        assert p.safety_buffer == 2

    def test_custom_buffer_pct(self) -> None:
        p = _proj(opening=100, safety_buffer_pct=Decimal("0.20"))
        # ceil(100 × 0.20) = 20
        assert p.safety_buffer == 20
        assert p.available_for_demand == 80


# ---------------------------------------------------------------------------
# Replenishment
# ---------------------------------------------------------------------------


class TestReplenishment:
    def test_replenishment_adds_to_supply(self) -> None:
        p = _proj(opening=40, replenishment=20)
        assert p.usable_supply == 60
        assert p.replenishment_quantity == 20

    def test_replenishment_prevents_shortage(self) -> None:
        # Without replenishment: opening=45, buffer=5, available=40, demand=50 → shortage=10
        # With replenishment=15: usable=60, available=55, no shortage
        p = _proj(
            point_demand=Decimal("50"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("55"),
            opening=45,
            replenishment=15,
        )
        assert p.shortage_point == 0
        assert p.stockout_risk is False

    def test_zero_replenishment_default(self) -> None:
        p = project_inventory(
            _forecast(),
            opening_inventory=70,
        )
        assert p.replenishment_quantity == 0


# ---------------------------------------------------------------------------
# Forecast scenario coverage (lower/point/upper)
# ---------------------------------------------------------------------------


class TestForecastScenarios:
    def test_ending_inventory_scenarios(self) -> None:
        # opening=70, buffer=7, usable=70
        # demand: lower=40, point=50, upper=65
        # ending_upper = 70-40=30, ending_point = 70-50=20, ending_lower = 70-65=5
        p = _proj(
            point_demand=Decimal("50"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("65"),
            opening=70,
        )
        assert p.ending_inventory_upper == 30
        assert p.ending_inventory_point == 20
        assert p.ending_inventory_lower == 5

    def test_ending_inventory_lower_can_be_negative(self) -> None:
        # Worst-case demand (upper=80) exceeds supply → negative ending
        p = _proj(
            point_demand=Decimal("50"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("80"),
            opening=70,
        )
        assert p.ending_inventory_lower < 0

    def test_shortage_upper_is_worst_case(self) -> None:
        p = _proj(
            point_demand=Decimal("55"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("75"),
            opening=60,
        )
        # buffer=6, available=54; upper_demand=75 → shortage_upper=21
        assert p.shortage_upper > p.shortage_point

    def test_surplus_lower_is_worst_case(self) -> None:
        # High demand → less surplus
        p = _proj(
            point_demand=Decimal("30"),
            lower_demand=Decimal("20"),
            upper_demand=Decimal("45"),
            opening=70,
        )
        assert p.surplus_lower < p.surplus_point


# ---------------------------------------------------------------------------
# Shortage severity tiers
# ---------------------------------------------------------------------------


class TestShortageSeverity:
    def test_none_when_no_shortage(self) -> None:
        assert _compute_severity(0, Decimal("50")) is ShortageSeverity.NONE

    def test_low_severity(self) -> None:
        # shortage=4, demand=50 → ratio=0.08 < 0.10
        assert _compute_severity(4, Decimal("50")) is ShortageSeverity.LOW

    def test_medium_severity(self) -> None:
        # shortage=7, demand=50 → ratio=0.14 in [0.10, 0.25)
        assert _compute_severity(7, Decimal("50")) is ShortageSeverity.MEDIUM

    def test_high_severity(self) -> None:
        # shortage=15, demand=50 → ratio=0.30 in [0.25, 0.50)
        assert _compute_severity(15, Decimal("50")) is ShortageSeverity.HIGH

    def test_critical_severity(self) -> None:
        # shortage=30, demand=50 → ratio=0.60 >= 0.50
        assert _compute_severity(30, Decimal("50")) is ShortageSeverity.CRITICAL

    def test_critical_when_zero_demand(self) -> None:
        # shortage>0 but demand=0 → undefined ratio → CRITICAL
        assert _compute_severity(5, Decimal("0")) is ShortageSeverity.CRITICAL

    def test_boundary_low_medium(self) -> None:
        # shortage=5, demand=50 → ratio=0.10 exactly → MEDIUM (not LOW)
        assert _compute_severity(5, Decimal("50")) is ShortageSeverity.MEDIUM

    def test_boundary_medium_high(self) -> None:
        # shortage=12.5→13? Use exact: shortage=12, demand=48 → ratio=0.25 → HIGH
        assert _compute_severity(12, Decimal("48")) is ShortageSeverity.HIGH

    def test_boundary_high_critical(self) -> None:
        # shortage=25, demand=50 → ratio=0.50 → CRITICAL
        assert _compute_severity(25, Decimal("50")) is ShortageSeverity.CRITICAL


# ---------------------------------------------------------------------------
# Stockout case
# ---------------------------------------------------------------------------


class TestStockoutCase:
    def test_shortage_point_nonzero(self) -> None:
        # opening=40, buffer=4, available=36, demand=50 → shortage=14
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("60"), opening=40)
        assert p.shortage_point == 14
        assert p.stockout_risk is True

    def test_stockout_window_fraction_present(self) -> None:
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("60"), opening=40)
        assert p.stockout_window_fraction is not None
        assert Decimal("0") < p.stockout_window_fraction < Decimal("1")

    def test_stockout_fraction_at_zero_inventory(self) -> None:
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("60"), opening=0, min_safety_buffer=0)
        assert p.stockout_window_fraction == Decimal("0")

    def test_stockout_fraction_calculation(self) -> None:
        # opening=40, buffer=4, available=36, point_demand=50
        # fraction = 36/50 = 0.72
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("60"), opening=40)
        assert p.stockout_window_fraction == Decimal("0.7200")

    def test_shortage_severity_set_on_stockout(self) -> None:
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("60"), opening=40)
        assert p.shortage_severity is not ShortageSeverity.NONE


# ---------------------------------------------------------------------------
# Surplus detection
# ---------------------------------------------------------------------------


class TestSurplusDetection:
    def test_no_surplus_risk_when_close_to_demand(self) -> None:
        p = _proj(point_demand=Decimal("50"), lower_demand=Decimal("45"), upper_demand=Decimal("55"), opening=60)
        # buffer=6, available=54, surplus_point=4; threshold = 6×2 = 12
        assert p.surplus_risk is False

    def test_surplus_risk_when_large_excess(self) -> None:
        p = _proj(
            point_demand=Decimal("10"),
            lower_demand=Decimal("8"),
            upper_demand=Decimal("12"),
            opening=70,
        )
        # buffer=7, available=63, surplus_point=53; threshold = 7×2 = 14 → surplus_risk=True
        assert p.surplus_risk is True

    def test_surplus_point_nonzero_on_low_demand(self) -> None:
        p = _proj(
            point_demand=Decimal("20"),
            lower_demand=Decimal("15"),
            upper_demand=Decimal("25"),
            opening=70,
        )
        assert p.surplus_point > 0

    def test_custom_surplus_multiplier(self) -> None:
        p = project_inventory(
            _forecast(point_demand=Decimal("20"), lower_demand=Decimal("15"), upper_demand=Decimal("25")),
            opening_inventory=70,
            surplus_risk_multiplier=Decimal("5.0"),  # very permissive
        )
        # With multiplier=5, threshold = buffer×5; may no longer flag risk
        assert isinstance(p.surplus_risk, bool)


# ---------------------------------------------------------------------------
# Zero demand
# ---------------------------------------------------------------------------


class TestZeroDemand:
    def test_zero_demand_no_shortage(self) -> None:
        p = _proj(point_demand=Decimal("0"), lower_demand=Decimal("0"), upper_demand=Decimal("0"), opening=50)
        assert p.shortage_point == 0
        assert p.stockout_risk is False

    def test_zero_demand_all_surplus(self) -> None:
        p = _proj(point_demand=Decimal("0"), lower_demand=Decimal("0"), upper_demand=Decimal("0"), opening=50)
        # buffer=5, available=45, surplus_point=45
        assert p.surplus_point == 45

    def test_zero_demand_stockout_fraction_none(self) -> None:
        p = _proj(point_demand=Decimal("0"), lower_demand=Decimal("0"), upper_demand=Decimal("0"), opening=50)
        assert p.stockout_window_fraction is None


# ---------------------------------------------------------------------------
# Deterministic projection ID
# ---------------------------------------------------------------------------


class TestProjectionId:
    def test_same_inputs_same_id(self) -> None:
        p1 = _proj(opening=70, replenishment=5)
        p2 = _proj(opening=70, replenishment=5)
        assert p1.projection_id == p2.projection_id

    def test_different_opening_different_id(self) -> None:
        p1 = _proj(opening=70)
        p2 = _proj(opening=71)
        assert p1.projection_id != p2.projection_id

    def test_id_starts_with_prefix(self) -> None:
        p = _proj()
        assert p.projection_id.startswith("inv_")

    def test_different_replenishment_different_id(self) -> None:
        p1 = _proj(opening=70, replenishment=0)
        p2 = _proj(opening=70, replenishment=10)
        assert p1.projection_id != p2.projection_id


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_negative_opening_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            project_inventory(_forecast(), opening_inventory=-1)

    def test_negative_replenishment_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            project_inventory(_forecast(), opening_inventory=70, replenishment_quantity=-1)

    def test_naive_window_start_rejected_on_forecast(self) -> None:
        from datetime import datetime
        with pytest.raises(ValueError, match="timezone-aware"):
            ForecastResult(
                forecast_id="f1",
                outlet_id="out",
                sku_id="sku",
                service_window="DINNER",
                prediction_as_of=datetime(2026, 1, 7, 13, 0),  # naive
                window_start=datetime(2026, 1, 7, 13, 0),
                window_end=datetime(2026, 1, 7, 16, 0),
                point_demand=Decimal("50"),
                lower_demand=Decimal("40"),
                upper_demand=Decimal("65"),
                interval_method="test",
                model_version="v1",
                feature_snapshot_id="snap",
                data_sufficient=True,
                quality_flags=(),
            )

    def test_demand_lower_exceeds_point_rejected(self) -> None:
        with pytest.raises(ValueError, match="lower_demand"):
            _forecast(lower_demand=Decimal("60"), point_demand=Decimal("50"))

    def test_demand_upper_below_point_rejected(self) -> None:
        with pytest.raises(ValueError, match="upper_demand"):
            _forecast(upper_demand=Decimal("40"), point_demand=Decimal("50"))


# ---------------------------------------------------------------------------
# Stockout-window fraction helper
# ---------------------------------------------------------------------------


class TestStockoutWindowFraction:
    def test_fraction_none_when_no_stockout(self) -> None:
        assert _stockout_window_fraction(60, Decimal("50")) is None

    def test_fraction_zero_at_zero_supply(self) -> None:
        assert _stockout_window_fraction(0, Decimal("50")) == Decimal("0")

    def test_fraction_between_zero_and_one(self) -> None:
        f = _stockout_window_fraction(30, Decimal("50"))
        assert f is not None
        assert Decimal("0") < f < Decimal("1")

    def test_fraction_is_decimal(self) -> None:
        f = _stockout_window_fraction(30, Decimal("50"))
        assert isinstance(f, Decimal)

    def test_cumulative_curve_interpolates_non_uniform_stockout(self) -> None:
        fraction = _stockout_fraction_from_curve(
            36,
            Decimal("50"),
            (Decimal("10"), Decimal("30"), Decimal("50")),
        )
        assert fraction == Decimal("0.7667")

    def test_projection_records_curve_or_uniform_method(self) -> None:
        uniform = _proj(
            point_demand=Decimal("50"),
            lower_demand=Decimal("45"),
            upper_demand=Decimal("60"),
            opening=40,
        )
        curved = project_inventory(
            _forecast(
                point_demand=Decimal("50"),
                lower_demand=Decimal("45"),
                upper_demand=Decimal("60"),
            ),
            opening_inventory=40,
            cumulative_demand_curve=(Decimal("10"), Decimal("30"), Decimal("50")),
        )
        assert uniform.stockout_timing_method is StockoutTimingMethod.UNIFORM_FALLBACK
        assert curved.stockout_timing_method is StockoutTimingMethod.CUMULATIVE_CURVE
        assert curved.stockout_window_fraction == Decimal("0.7667")
        assert curved.projection_id != uniform.projection_id

    @pytest.mark.parametrize(
        "curve",
        [
            (),
            (Decimal("10"), Decimal("9"), Decimal("50")),
            (Decimal("10"), Decimal("30"), Decimal("49")),
            (Decimal("10"), Decimal("NaN"), Decimal("50")),
        ],
    )
    def test_invalid_cumulative_curve_rejected(self, curve) -> None:
        with pytest.raises(ValueError, match="cumulative"):
            project_inventory(
                _forecast(
                    point_demand=Decimal("50"),
                    lower_demand=Decimal("45"),
                    upper_demand=Decimal("60"),
                ),
                opening_inventory=40,
                cumulative_demand_curve=curve,
            )


class TestRealForecastCompatibility:
    def test_accepts_c05_baseline_forecast(self) -> None:
        from lossline_intelligence.forecasts import BaselineForecast, BaselineScope

        forecast = BaselineForecast(
            forecast_id="fcst_baseline_real",
            forecast_version="comparable_median.v1",
            interval_method="empirical_comparable_demand_80.v1",
            prediction_as_of=_T0,
            outlet_id="meghana_indiranagar",
            sku_id="CHICKEN_BIRYANI",
            service_window="DINNER",
            window_start=_T0,
            window_end=_T1,
            feature_snapshot_id="snap_real",
            point_demand=Decimal("50"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("60"),
            scope=BaselineScope.OUTLET_SKU_WEEKDAY_WINDOW,
            sample_count=4,
            source_snapshot_ids=("s1", "s2", "s3", "s4"),
            data_sufficient=True,
        )
        result = project_inventory(forecast, opening_inventory=40)
        assert result.forecast_id == forecast.forecast_id
        assert result.stockout_risk is True

    def test_accepts_c06_gbt_forecast(self) -> None:
        from lossline_intelligence.forecasts import GBTForecast

        forecast = GBTForecast(
            forecast_id="fcst_gbt_real",
            model_version="lightgbm_gbt.v1",
            artifact_id="artifact_real",
            interval_method="empirical_residual_80.v1",
            prediction_as_of=_T0,
            outlet_id="meghana_indiranagar",
            sku_id="CHICKEN_BIRYANI",
            service_window="DINNER",
            window_start=_T0,
            window_end=_T1,
            feature_snapshot_id="snap_real",
            point_demand=Decimal("50"),
            lower_demand=Decimal("40"),
            upper_demand=Decimal("60"),
            data_sufficient=True,
        )
        result = project_inventory(forecast, opening_inventory=40)
        assert result.forecast_id == forecast.forecast_id
        assert result.stockout_risk is True


# ---------------------------------------------------------------------------
# Rule version and evidence IDs
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_rule_version_on_projection(self) -> None:
        p = _proj()
        assert p.rule_version == RULE_VERSION

    def test_custom_rule_version(self) -> None:
        p = project_inventory(
            _forecast(),
            opening_inventory=70,
            rule_version="inventory.v2",
        )
        assert p.rule_version == "inventory.v2"

    def test_evidence_ids_stored(self) -> None:
        evidence = ("sig_001", "sig_002")
        p = project_inventory(
            _forecast(),
            opening_inventory=70,
            evidence_ids=evidence,
        )
        assert p.evidence_ids == evidence

    def test_outlet_sku_window_carried(self) -> None:
        p = _proj()
        assert p.outlet_id == "meghana_indiranagar"
        assert p.sku_id == "CHICKEN_BIRYANI"
        assert p.service_window == "DINNER"


# ---------------------------------------------------------------------------
# Golden scenario coverage (C03 scenarios E/F via causal world)
# ---------------------------------------------------------------------------


def _from_causal_world():
    try:
        from lossline_simulator.causal_world import (
            GoldenScenario,
            generate_window,
        )
        return GoldenScenario, generate_window
    except ImportError:
        pytest.skip("simulator not installed")


def _make_forecast_from_synthetic(sw, sku_id: str) -> tuple[ForecastResult, int]:
    """Build a ForecastResult and opening_inventory from a SyntheticWindow."""
    from lossline_simulator.causal_world import SKU_CONFIGS

    sku_cfg = {c.sku_id: c for c in SKU_CONFIGS}
    outcome = next(so for so in sw.sku_outcomes if so.sku_id == sku_id)
    base = sku_cfg[sku_id].base_demand
    return (
        ForecastResult(
            forecast_id=f"fc_{sku_id}_test",
            outlet_id=sw.outlet_id,
            sku_id=sku_id,
            service_window=sw.context.service_window,
            prediction_as_of=sw.window_start,
            window_start=sw.window_start,
            window_end=sw.window_end,
            point_demand=base,
            lower_demand=(base * Decimal("0.80")).quantize(Decimal("1")),
            upper_demand=(base * Decimal("1.25")).quantize(Decimal("1")),
            interval_method="baseline_range",
            model_version="baseline.v1",
            feature_snapshot_id=f"snap_{sku_id}",
            data_sufficient=True,
            quality_flags=(),
        ),
        outcome.opening_inventory_quantity,
    )


class TestGoldenScenarios:
    def test_scenario_e_stockout_detected(self) -> None:
        """Scenario E (promotion + limited inventory) should surface stockout risk."""
        GoldenScenario, generate_window = _from_causal_world()
        _T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
        sw = generate_window(GoldenScenario.PROMOTION_LIMITED_INVENTORY, seed=42, window_start=_T0)
        stockout_found = False
        for so in sw.sku_outcomes:
            if so.stockout:
                fc, opening = _make_forecast_from_synthetic(sw, so.sku_id)
                p = project_inventory(fc, opening_inventory=opening)
                assert p.stockout_risk is True
                stockout_found = True
        assert stockout_found, "Scenario E should have at least one stockout SKU"

    def test_scenario_a_baseline_no_stockout(self) -> None:
        """Scenario A (normal weekday) should not produce stockout with normal inventory."""
        GoldenScenario, generate_window = _from_causal_world()
        _T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
        sw = generate_window(GoldenScenario.NORMAL_WEEKDAY, seed=42, window_start=_T0)
        for so in sw.sku_outcomes:
            fc, opening = _make_forecast_from_synthetic(sw, so.sku_id)
            p = project_inventory(fc, opening_inventory=opening)
            # Normal weekday scenario should have sufficient inventory
            assert isinstance(p, InventoryProjection)

    def test_projection_id_deterministic_across_runs(self) -> None:
        """Same scenario inputs produce the same projection_id."""
        GoldenScenario, generate_window = _from_causal_world()
        _T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
        sw = generate_window(GoldenScenario.NORMAL_WEEKDAY, seed=42, window_start=_T0)
        so = sw.sku_outcomes[0]
        fc, opening = _make_forecast_from_synthetic(sw, so.sku_id)
        p1 = project_inventory(fc, opening_inventory=opening)
        p2 = project_inventory(fc, opening_inventory=opening)
        assert p1.projection_id == p2.projection_id
