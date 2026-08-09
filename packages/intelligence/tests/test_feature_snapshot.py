"""C04 feature pipeline tests.

Covers: snapshot identity, fingerprint determinism and sensitivity, registry
validation, missing features, censored-demand targets, future/late-record
exclusion, quality flags, service window UTC resolution, golden scenario
coverage (A--G), dataset builder with lag features, and dataset fingerprint
reproducibility.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.features.catalog import build_demo_registry
from lossline_intelligence.features.pipeline import (
    SkuFeatureInput,
    WindowFeatureInput,
    build_dataset,
    build_snapshot,
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
from lossline_intelligence.features.windows import (
    DINNER_WINDOW,
    LUNCH_WINDOW,
    ServiceWindowConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)  # Wednesday
_T1 = _T0 + timedelta(hours=3)


def _sku(
    sku_id: str = "CHICKEN_BIRYANI",
    base_demand: Decimal = Decimal("52"),
    workload_minutes: Decimal = Decimal("8"),
    opening_inventory: int = 70,
    promoted: bool = False,
    promotion_discount: Decimal | None = None,
    latent_demand: int = 52,
    fulfilled: int = 52,
    stockout: bool = False,
) -> SkuFeatureInput:
    return SkuFeatureInput(
        sku_id=sku_id,
        base_demand=base_demand,
        workload_minutes=workload_minutes,
        opening_inventory=opening_inventory,
        promoted=promoted,
        promotion_discount=promotion_discount,
        latent_demand=latent_demand,
        fulfilled=fulfilled,
        stockout=stockout,
    )


def _window(
    *,
    skus: tuple[SkuFeatureInput, ...] | None = None,
    window_start: datetime = _T0,
    window_end: datetime = _T1,
    weekday: int = 2,
    weather_state: str = "CLEAR",
    rainfall_mm: Decimal | None = Decimal("0"),
    is_holiday: bool = False,
    local_event: bool = False,
    delivery_share: Decimal = Decimal("0.40"),
    data_quality: Decimal = Decimal("1"),
    available_capacity_minutes: Decimal = Decimal("900"),
) -> WindowFeatureInput:
    return WindowFeatureInput(
        outlet_id="meghana_indiranagar",
        service_window="DINNER",
        window_start=window_start,
        window_end=window_end,
        weekday=weekday,
        weather_state=weather_state,
        rainfall_mm=rainfall_mm,
        is_holiday=is_holiday,
        local_event=local_event,
        delivery_share=delivery_share,
        data_quality=data_quality,
        available_capacity_minutes=available_capacity_minutes,
        sku_inputs=skus if skus is not None else (_sku(),),
    )


def _as_of() -> datetime:
    """Default prediction_as_of after window end (for training)."""
    return _T1 + timedelta(minutes=1)


# ---------------------------------------------------------------------------
# Snapshot identity and fingerprint
# ---------------------------------------------------------------------------


class TestFingerprint:
    def test_deterministic_fingerprint(self) -> None:
        registry = build_demo_registry()
        w = _window()
        s = w.sku_inputs[0]
        snap_a = build_snapshot(w, s, registry=registry, prediction_as_of=_as_of())
        snap_b = build_snapshot(w, s, registry=registry, prediction_as_of=_as_of())
        assert snap_a.fingerprint == snap_b.fingerprint

    def test_fingerprint_sensitivity(self) -> None:
        registry = build_demo_registry()
        w1 = _window(delivery_share=Decimal("0.40"))
        w2 = _window(delivery_share=Decimal("0.60"))
        s = _sku()
        snap_a = build_snapshot(w1, s, registry=registry, prediction_as_of=_as_of())
        snap_b = build_snapshot(w2, s, registry=registry, prediction_as_of=_as_of())
        assert snap_a.fingerprint != snap_b.fingerprint

    def test_snapshot_id_deterministic(self) -> None:
        id_a = compute_snapshot_id("out", "sku", "DINNER", _T0, _as_of(), PIPELINE_VERSION)
        id_b = compute_snapshot_id("out", "sku", "DINNER", _T0, _as_of(), PIPELINE_VERSION)
        assert id_a == id_b
        assert id_a.startswith("snap_out_sku_")

    def test_snapshot_id_different_grain(self) -> None:
        id_a = compute_snapshot_id("out", "sku_A", "DINNER", _T0, _as_of(), PIPELINE_VERSION)
        id_b = compute_snapshot_id("out", "sku_B", "DINNER", _T0, _as_of(), PIPELINE_VERSION)
        assert id_a != id_b

    def test_fingerprint_function_type_safety(self) -> None:
        """Bool and int are encoded distinctly (bool is not coerced to int)."""
        fp_bool = compute_fingerprint(
            {"flag": True}, PIPELINE_VERSION, "reg_fp"
        )
        fp_int = compute_fingerprint(
            {"flag": 1}, PIPELINE_VERSION, "reg_fp"
        )
        assert fp_bool != fp_int


# ---------------------------------------------------------------------------
# Registry validation
# ---------------------------------------------------------------------------


class TestRegistryValidation:
    def test_valid_snapshot_accepted(self) -> None:
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        assert isinstance(snap, FeatureSnapshot)
        assert snap.registry_version == registry.registry_version
        assert snap.registry_fingerprint == registry.fingerprint

    def test_all_registered_features_present(self) -> None:
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        registered_ids = {d.feature_id for d in registry.definitions}
        assert set(snap.feature_values.keys()) == registered_ids


# ---------------------------------------------------------------------------
# Missing features
# ---------------------------------------------------------------------------


class TestMissingFeatures:
    def test_missing_rainfall(self) -> None:
        """Missing weather rainfall is tracked as missing."""
        registry = build_demo_registry()
        w = _window(rainfall_mm=None)
        snap = build_snapshot(w, _sku(), registry=registry, prediction_as_of=_as_of())
        assert "weather.rainfall_mm" in snap.missing_features
        assert snap.feature_values["weather.rainfall_mm"] is None

    def test_missing_lag_first_window(self) -> None:
        """First window has no lag data — feature is missing."""
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        assert "demand.fulfilled_quantity.lag1" in snap.missing_features

    def test_imputed_promotion_discount(self) -> None:
        """Non-promoted SKU gets discount imputed to zero."""
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(promoted=False), registry=registry, prediction_as_of=_as_of()
        )
        assert "promotion.discount_pct" in snap.imputed_features
        assert snap.feature_values["promotion.discount_pct"] == Decimal("0")

    def test_data_sufficiency_false_when_missing(self) -> None:
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        # Lag is missing on first window
        assert snap.quality.data_sufficiency is False

    def test_data_sufficiency_true_when_complete(self) -> None:
        registry = build_demo_registry()
        w = _window()
        s = _sku()
        prior_end = _T0 - timedelta(seconds=1)
        snap = build_snapshot(
            w, s, registry=registry, prediction_as_of=_as_of(),
            prior_sku_fulfilled=48, prior_window_end=prior_end,
        )
        assert snap.quality.data_sufficiency is True
        assert len(snap.missing_features) == 0


# ---------------------------------------------------------------------------
# Censored-demand target handling
# ---------------------------------------------------------------------------


class TestCensoredTarget:
    def test_stockout_flagged(self) -> None:
        """Stockout SKU marks censored_target in quality."""
        registry = build_demo_registry()
        s = _sku(
            opening_inventory=40,
            latent_demand=55,
            fulfilled=40,
            stockout=True,
        )
        snap = build_snapshot(_window(), s, registry=registry, prediction_as_of=_as_of())
        assert snap.quality.censored_target is True

    def test_no_stockout_not_censored(self) -> None:
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        assert snap.quality.censored_target is False

    def test_dataset_row_censored_flag(self) -> None:
        """DatasetRow carries separate censored flag and both quantities."""
        registry = build_demo_registry()
        s = _sku(
            latent_demand=60,
            fulfilled=45,
            opening_inventory=45,
            stockout=True,
        )
        rows = build_dataset(
            [_window(skus=(s,))],
            registry=registry,
            prediction_as_of=_as_of(),
        )
        row = rows[0]
        assert row.censored is True
        assert row.target_demand_quantity == 60
        assert row.observed_demand_quantity == 45
        assert row.target_demand_quantity > row.observed_demand_quantity


# ---------------------------------------------------------------------------
# Future and late-record exclusion
# ---------------------------------------------------------------------------


class TestFutureExclusion:
    def test_lag_excluded_when_prior_window_after_prediction(self) -> None:
        """Lag from a window ending after prediction_as_of is NOT used."""
        registry = build_demo_registry()
        # Prior window ends at _T1; prediction_as_of = _T0 (BEFORE prior end)
        snap = build_snapshot(
            _window(),
            _sku(),
            registry=registry,
            prediction_as_of=_T0,  # before prior window end
            prior_sku_fulfilled=48,
            prior_window_end=_T1,  # ends AFTER prediction_as_of
        )
        assert "demand.fulfilled_quantity.lag1" in snap.missing_features
        assert snap.feature_values["demand.fulfilled_quantity.lag1"] is None

    def test_lag_included_when_prior_window_before_prediction(self) -> None:
        """Lag from a window ending before prediction_as_of IS used."""
        registry = build_demo_registry()
        prior_end = _T0 - timedelta(hours=1)
        snap = build_snapshot(
            _window(),
            _sku(),
            registry=registry,
            prediction_as_of=_as_of(),
            prior_sku_fulfilled=48,
            prior_window_end=prior_end,
        )
        assert "demand.fulfilled_quantity.lag1" not in snap.missing_features
        assert snap.feature_values["demand.fulfilled_quantity.lag1"] == 48

    def test_naive_prediction_as_of_rejected(self) -> None:
        """Naive (no timezone) prediction_as_of raises."""
        registry = build_demo_registry()
        with pytest.raises(ValueError, match="timezone-aware"):
            build_snapshot(
                _window(),
                _sku(),
                registry=registry,
                prediction_as_of=datetime(2026, 1, 7, 13, 0),  # naive
            )

    def test_lag_at_boundary_included(self) -> None:
        """Prior window ending exactly at prediction_as_of is included."""
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(),
            _sku(),
            registry=registry,
            prediction_as_of=_T0,
            prior_sku_fulfilled=48,
            prior_window_end=_T0,  # exactly at prediction_as_of
        )
        assert "demand.fulfilled_quantity.lag1" not in snap.missing_features


# ---------------------------------------------------------------------------
# Quality flags
# ---------------------------------------------------------------------------


class TestQualityFlags:
    def test_completeness_fraction(self) -> None:
        registry = build_demo_registry()
        snap = build_snapshot(
            _window(), _sku(), registry=registry, prediction_as_of=_as_of()
        )
        total = len(registry.definitions)
        missing_count = len(snap.missing_features)
        expected = Decimal(total - missing_count) / Decimal(total)
        assert snap.quality.completeness == expected.quantize(Decimal("0.0001"))

    def test_data_quality_from_context(self) -> None:
        registry = build_demo_registry()
        w = _window(data_quality=Decimal("0.75"))
        snap = build_snapshot(w, _sku(), registry=registry, prediction_as_of=_as_of())
        assert snap.quality.data_quality_score == Decimal("0.75")


# ---------------------------------------------------------------------------
# Service window UTC resolution
# ---------------------------------------------------------------------------


class TestServiceWindow:
    def test_dinner_window_utc(self) -> None:
        start, end = DINNER_WINDOW.resolve_utc(date(2026, 1, 7))
        # Asia/Kolkata is UTC+5:30
        assert start == datetime(2026, 1, 7, 13, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 1, 7, 16, 0, tzinfo=timezone.utc)

    def test_lunch_window_utc(self) -> None:
        start, end = LUNCH_WINDOW.resolve_utc(date(2026, 1, 7))
        assert start == datetime(2026, 1, 7, 6, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 1, 7, 9, 0, tzinfo=timezone.utc)

    def test_invalid_timezone_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid timezone"):
            ServiceWindowConfig(
                window_name="TEST",
                start_local=datetime(2026, 1, 1, 11, 0).time(),
                end_local=datetime(2026, 1, 1, 14, 0).time(),
                timezone_name="Not/A/Timezone",
            )

    def test_inverted_window_rejected(self) -> None:
        from datetime import time

        with pytest.raises(ValueError, match="start_local must be before"):
            ServiceWindowConfig(
                window_name="BAD",
                start_local=time(21, 0),
                end_local=time(18, 0),
                timezone_name="Asia/Kolkata",
            )


# ---------------------------------------------------------------------------
# Golden scenario coverage (A--G via synthetic converter)
# ---------------------------------------------------------------------------


def _from_causal_world():
    """Import causal world only when available (soft test dependency)."""
    try:
        from lossline_simulator.causal_world import (
            GoldenScenario,
            SyntheticWindow,
            generate_golden_scenarios,
            generate_window,
        )
        return GoldenScenario, SyntheticWindow, generate_golden_scenarios, generate_window
    except ImportError:
        pytest.skip("simulator not installed")


def _synthetic_to_window_input(sw) -> WindowFeatureInput:
    """Convert a SyntheticWindow to a pipeline WindowFeatureInput."""
    # Import SKU_CONFIGS for per-unit workload (SyntheticSkuOutcome.workload_minutes
    # is total = demand × per_unit, but the feature needs per_unit from the catalog)
    from lossline_simulator.causal_world import SKU_CONFIGS

    sku_workload = {cfg.sku_id: cfg.workload_minutes for cfg in SKU_CONFIGS}
    skus = tuple(
        SkuFeatureInput(
            sku_id=so.sku_id,
            base_demand=so.baseline_demand,
            workload_minutes=sku_workload[so.sku_id],
            opening_inventory=so.opening_inventory_quantity,
            promoted=sw.context.promoted_sku_id == so.sku_id,
            promotion_discount=sw.context.promotion_discount if sw.context.promoted_sku_id == so.sku_id else None,
            latent_demand=so.latent_demand_quantity,
            fulfilled=so.fulfilled_quantity,
            stockout=so.stockout,
        )
        for so in sw.sku_outcomes
    )
    return WindowFeatureInput(
        outlet_id=sw.outlet_id,
        service_window=sw.context.service_window,
        window_start=sw.window_start,
        window_end=sw.window_end,
        weekday=sw.context.weekday,
        weather_state=sw.context.weather.value,
        rainfall_mm=sw.context.rainfall_mm,
        is_holiday=sw.context.holiday,
        local_event=sw.context.local_event,
        delivery_share=sw.context.delivery_share,
        data_quality=sw.context.data_quality,
        available_capacity_minutes=sw.available_capacity_minutes,
        sku_inputs=skus,
    )


class TestGoldenScenarios:
    def test_all_scenarios_produce_valid_snapshots(self) -> None:
        GoldenScenario, _, generate_golden_scenarios, _ = _from_causal_world()
        registry = build_demo_registry()
        scenarios = generate_golden_scenarios(seed=42, window_start=_T0)
        for sw in scenarios:
            w = _synthetic_to_window_input(sw)
            for s in w.sku_inputs:
                snap = build_snapshot(
                    w, s, registry=registry, prediction_as_of=_as_of()
                )
                assert isinstance(snap, FeatureSnapshot)
                assert snap.outlet_id == sw.outlet_id

    def test_scenario_e_stockout_censored(self) -> None:
        """Scenario E (promotion + limited inventory) has censored targets."""
        GoldenScenario, _, _, generate_window = _from_causal_world()
        registry = build_demo_registry()
        sw = generate_window(
            GoldenScenario.PROMOTION_LIMITED_INVENTORY,
            seed=42,
            window_start=_T0,
        )
        w = _synthetic_to_window_input(sw)
        for s in w.sku_inputs:
            snap = build_snapshot(w, s, registry=registry, prediction_as_of=_as_of())
            if s.stockout:
                assert snap.quality.censored_target is True

    def test_scenario_g_missing_weather(self) -> None:
        """Scenario G (missing weather) has rainfall as missing."""
        GoldenScenario, _, _, generate_window = _from_causal_world()
        registry = build_demo_registry()
        sw = generate_window(
            GoldenScenario.MISSING_WEATHER,
            seed=42,
            window_start=_T0,
        )
        w = _synthetic_to_window_input(sw)
        snap = build_snapshot(
            w, w.sku_inputs[0], registry=registry, prediction_as_of=_as_of()
        )
        assert "weather.rainfall_mm" in snap.missing_features
        assert snap.quality.data_quality_score == Decimal("0.75")


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------


class TestDatasetBuilder:
    def test_multi_window_row_count(self) -> None:
        """Two windows × 1 SKU = 2 rows."""
        registry = build_demo_registry()
        w1 = _window(window_start=_T0, window_end=_T1)
        w2 = _window(
            window_start=_T1,
            window_end=_T1 + timedelta(hours=3),
        )
        rows = build_dataset(
            [w1, w2], registry=registry, prediction_as_of=_as_of() + timedelta(hours=3)
        )
        assert len(rows) == 2

    def test_lag_populated_on_second_window(self) -> None:
        """Second window gets lag feature from first window."""
        registry = build_demo_registry()
        w1 = _window(window_start=_T0, window_end=_T1)
        w2 = _window(
            window_start=_T1,
            window_end=_T1 + timedelta(hours=3),
        )
        as_of = _T1 + timedelta(hours=3, minutes=1)
        rows = build_dataset([w1, w2], registry=registry, prediction_as_of=as_of)
        # First row: lag missing
        assert "demand.fulfilled_quantity.lag1" in rows[0].snapshot.missing_features
        # Second row: lag present
        assert "demand.fulfilled_quantity.lag1" not in rows[1].snapshot.missing_features
        assert rows[1].snapshot.feature_values["demand.fulfilled_quantity.lag1"] == 52

    def test_multi_sku_rows(self) -> None:
        """Three SKUs × 1 window = 3 rows."""
        registry = build_demo_registry()
        skus = (
            _sku(sku_id="CHICKEN_BIRYANI"),
            _sku(sku_id="MUTTON_BIRYANI", base_demand=Decimal("28"), workload_minutes=Decimal("10")),
            _sku(sku_id="ALOO_BIRYANI", base_demand=Decimal("20"), workload_minutes=Decimal("6")),
        )
        w = _window(skus=skus)
        rows = build_dataset([w], registry=registry, prediction_as_of=_as_of())
        assert len(rows) == 3
        sku_ids = [row.snapshot.sku_id for row in rows]
        assert sku_ids == ["CHICKEN_BIRYANI", "MUTTON_BIRYANI", "ALOO_BIRYANI"]


# ---------------------------------------------------------------------------
# Dataset fingerprint
# ---------------------------------------------------------------------------


class TestDatasetFingerprint:
    def test_reproducible(self) -> None:
        registry = build_demo_registry()
        w = _window()
        rows_a = build_dataset([w], registry=registry, prediction_as_of=_as_of())
        rows_b = build_dataset([w], registry=registry, prediction_as_of=_as_of())
        fp_a = compute_dataset_fingerprint(rows_a)
        fp_b = compute_dataset_fingerprint(rows_b)
        assert fp_a == fp_b

    def test_different_data_different_fingerprint(self) -> None:
        registry = build_demo_registry()
        w1 = _window(delivery_share=Decimal("0.40"))
        w2 = _window(delivery_share=Decimal("0.80"))
        rows_a = build_dataset([w1], registry=registry, prediction_as_of=_as_of())
        rows_b = build_dataset([w2], registry=registry, prediction_as_of=_as_of())
        fp_a = compute_dataset_fingerprint(rows_a)
        fp_b = compute_dataset_fingerprint(rows_b)
        assert fp_a != fp_b

    def test_golden_scenarios_dataset(self) -> None:
        """Full A--G dataset produces a stable fingerprint."""
        _, _, generate_golden_scenarios, _ = _from_causal_world()
        registry = build_demo_registry()
        scenarios = generate_golden_scenarios(seed=42, window_start=_T0)
        inputs = [_synthetic_to_window_input(sw) for sw in scenarios]
        as_of = _T1 + timedelta(hours=1)
        rows = build_dataset(inputs, registry=registry, prediction_as_of=as_of)
        fp_1 = compute_dataset_fingerprint(rows)
        # Re-run with same inputs
        rows_2 = build_dataset(inputs, registry=registry, prediction_as_of=as_of)
        fp_2 = compute_dataset_fingerprint(rows_2)
        assert fp_1 == fp_2
        # 7 scenarios × 3 SKUs = 21 rows
        assert len(rows) == 21


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_naive_window_start_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            WindowFeatureInput(
                outlet_id="out",
                service_window="DINNER",
                window_start=datetime(2026, 1, 7, 13, 0),  # naive
                window_end=datetime(2026, 1, 7, 16, 0, tzinfo=timezone.utc),
                weekday=2,
                weather_state="CLEAR",
                rainfall_mm=Decimal("0"),
                is_holiday=False,
                local_event=False,
                delivery_share=Decimal("0.40"),
                data_quality=Decimal("1"),
                available_capacity_minutes=Decimal("900"),
                sku_inputs=(_sku(),),
            )

    def test_empty_sku_inputs_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one SKU"):
            WindowFeatureInput(
                outlet_id="out",
                service_window="DINNER",
                window_start=_T0,
                window_end=_T1,
                weekday=2,
                weather_state="CLEAR",
                rainfall_mm=Decimal("0"),
                is_holiday=False,
                local_event=False,
                delivery_share=Decimal("0.40"),
                data_quality=Decimal("1"),
                available_capacity_minutes=Decimal("900"),
                sku_inputs=(),
            )

    def test_inverted_window_rejected(self) -> None:
        with pytest.raises(ValueError, match="window_end must be after"):
            WindowFeatureInput(
                outlet_id="out",
                service_window="DINNER",
                window_start=_T1,
                window_end=_T0,  # before start
                weekday=2,
                weather_state="CLEAR",
                rainfall_mm=Decimal("0"),
                is_holiday=False,
                local_event=False,
                delivery_share=Decimal("0.40"),
                data_quality=Decimal("1"),
                available_capacity_minutes=Decimal("900"),
                sku_inputs=(_sku(),),
            )
