from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.evaluation import (
    AcceptanceStatus,
    DemandBand,
    EvaluationStatus,
    ForecastEvaluationRow,
    ForecastMetricSummary,
    ForecastModelKind,
    SubgroupComparison,
    assess_model_acceptance,
    compare_subgroups,
    compute_metric_summary,
    evaluate_rolling_origin,
)
from lossline_intelligence.features import build_demo_registry
from lossline_intelligence.features.pipeline import (
    SkuFeatureInput,
    WindowFeatureInput,
    build_snapshot,
)
from lossline_intelligence.features.snapshot import DatasetRow


T0 = datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc)
REGISTRY = build_demo_registry()


def evaluation_row(
    model_kind: ForecastModelKind,
    *,
    prediction: int,
    actual: int,
    outlet_id: str = "outlet_a",
    sku_id: str = "sku_a",
    index: int = 0,
) -> ForecastEvaluationRow:
    start = T0 + timedelta(days=index)
    predicted = Decimal(prediction)
    observed = Decimal(actual)
    signed = predicted - observed
    return ForecastEvaluationRow(
        evaluation_id=f"eval_{model_kind.value}_{index}_{outlet_id}_{sku_id}",
        evaluation_version="forecast_evaluation.v1",
        model_kind=model_kind,
        forecast_id=f"forecast_{model_kind.value}_{index}_{outlet_id}_{sku_id}",
        model_version="v1",
        training_cutoff=start - timedelta(hours=1),
        prediction_as_of=start,
        window_start=start,
        window_end=start + timedelta(hours=3),
        outlet_id=outlet_id,
        sku_id=sku_id,
        service_window="DINNER",
        demand_band=(
            DemandBand.ZERO
            if actual == 0
            else DemandBand.LOW if actual <= 10 else DemandBand.MEDIUM
        ),
        status=EvaluationStatus.EVALUATED,
        prediction=predicted,
        lower_bound=max(Decimal("0"), predicted - Decimal("2")),
        upper_bound=predicted + Decimal("2"),
        actual=observed,
        absolute_error=abs(signed),
        percentage_error=None if actual == 0 else abs(signed) / observed,
        signed_error=signed,
        interval_hit=predicted - Decimal("2") <= observed <= predicted + Decimal("2"),
    )


def dataset_row(index: int, demand: int, *, censored: bool = False) -> DatasetRow:
    start = T0 + timedelta(days=7 * index)
    fulfilled = demand - 3 if censored else demand
    sku = SkuFeatureInput(
        sku_id="sku_a",
        base_demand=Decimal("20"),
        workload_minutes=Decimal("8"),
        opening_inventory=max(0, fulfilled),
        promoted=index % 5 == 0,
        promotion_discount=Decimal("0.1") if index % 5 == 0 else None,
        latent_demand=demand,
        fulfilled=max(0, fulfilled),
        stockout=censored,
    )
    window = WindowFeatureInput(
        outlet_id="outlet_a",
        service_window="DINNER",
        window_start=start,
        window_end=start + timedelta(hours=3),
        weekday=2,
        weather_state="RAIN" if index % 4 == 0 else "CLEAR",
        rainfall_mm=Decimal("10") if index % 4 == 0 else Decimal("0"),
        is_holiday=index % 11 == 0,
        local_event=False,
        delivery_share=Decimal("0.4") + Decimal(index % 3) / Decimal("10"),
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
    return DatasetRow(snapshot, demand, max(0, fulfilled), censored)


def summary(kind: ForecastModelKind, wmape: str | None, count: int = 10):
    value = None if wmape is None else Decimal(wmape)
    return ForecastMetricSummary(
        model_kind=kind,
        evaluated_count=count,
        censored_count=0,
        abstention_count=0,
        mae=value,
        rmse=value,
        wmape=value,
        bias=Decimal("0") if value is not None else None,
        interval_coverage=Decimal("0.8") if value is not None else None,
        mean_interval_width=Decimal("4") if value is not None else None,
    )


def test_metric_summary_calculates_required_metrics_and_coverage() -> None:
    rows = (
        evaluation_row(ForecastModelKind.BASELINE, prediction=12, actual=10, index=0),
        evaluation_row(ForecastModelKind.BASELINE, prediction=16, actual=20, index=1),
    )
    result = compute_metric_summary(rows, ForecastModelKind.BASELINE)

    assert result.evaluated_count == 2
    assert result.mae == Decimal("3.0000")
    assert result.rmse == Decimal("3.1623")
    assert result.wmape == Decimal("0.2000")
    assert result.bias == Decimal("-1.0000")
    assert result.interval_coverage == Decimal("0.5000")
    assert result.mean_interval_width == Decimal("4.0000")


def test_zero_actual_wmape_is_unavailable() -> None:
    result = compute_metric_summary(
        (evaluation_row(ForecastModelKind.GBT, prediction=0, actual=0),),
        ForecastModelKind.GBT,
    )
    assert result.wmape is None
    assert result.mae == Decimal("0.0000")


def test_acceptance_requires_five_percent_improvement() -> None:
    accepted = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, "0.20"),
        summary(ForecastModelKind.GBT, "0.18"),
        (),
    )
    rejected = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, "0.20"),
        summary(ForecastModelKind.GBT, "0.191"),
        (),
    )

    assert accepted.status is AcceptanceStatus.ACCEPTED
    assert accepted.relative_improvement == Decimal("0.1000")
    assert rejected.status is AcceptanceStatus.REJECTED


def test_acceptance_rejects_subgroup_regression() -> None:
    subgroup = SubgroupComparison(
        dimension="sku_id",
        value="sku_b",
        baseline=summary(ForecastModelKind.BASELINE, "0.10"),
        model=summary(ForecastModelKind.GBT, "0.12"),
        relative_wmape_regression=Decimal("0.20"),
        exceeds_limit=True,
    )
    result = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, "0.20"),
        summary(ForecastModelKind.GBT, "0.15"),
        (subgroup,),
    )

    assert result.status is AcceptanceStatus.REJECTED
    assert result.failing_subgroups == ("sku_id=sku_b",)


def test_acceptance_honors_custom_subgroup_limit() -> None:
    subgroup = SubgroupComparison(
        dimension="sku_id",
        value="sku_b",
        baseline=summary(ForecastModelKind.BASELINE, "0.10"),
        model=summary(ForecastModelKind.GBT, "0.12"),
        relative_wmape_regression=Decimal("0.20"),
        exceeds_limit=True,
    )
    result = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, "0.20"),
        summary(ForecastModelKind.GBT, "0.15"),
        (subgroup,),
        max_subgroup_regression=Decimal("0.25"),
    )

    assert result.status is AcceptanceStatus.ACCEPTED
    assert result.failing_subgroups == ()


def test_acceptance_reports_insufficient_evidence() -> None:
    result = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, None, count=0),
        summary(ForecastModelKind.GBT, "0.10"),
        (),
    )
    assert result.status is AcceptanceStatus.INSUFFICIENT_EVIDENCE


def test_acceptance_requires_paired_evaluation_counts() -> None:
    result = assess_model_acceptance(
        summary(ForecastModelKind.BASELINE, "0.20", count=10),
        summary(ForecastModelKind.GBT, "0.10", count=9),
        (),
    )

    assert result.status is AcceptanceStatus.INSUFFICIENT_EVIDENCE


def test_subgroups_cover_outlet_sku_window_and_demand_band() -> None:
    rows = (
        evaluation_row(ForecastModelKind.BASELINE, prediction=12, actual=10),
        evaluation_row(ForecastModelKind.GBT, prediction=11, actual=10),
    )
    comparisons = compare_subgroups(rows)
    assert {item.dimension for item in comparisons} == {
        "outlet_id",
        "sku_id",
        "service_window",
        "demand_band",
    }


def test_rolling_origin_is_repeatable_and_leakage_safe() -> None:
    rows = tuple(dataset_row(i, 20 + i + (i % 3)) for i in range(30))
    params = {"n_estimators": 15, "num_leaves": 7, "seed": 42}

    first = evaluate_rolling_origin(rows, initial_history_rows=25, gbt_params=params)
    second = evaluate_rolling_origin(rows, initial_history_rows=25, gbt_params=params)

    assert first.report_id == second.report_id
    assert first.rows == second.rows
    assert len(first.rows) == 10
    assert all(
        item.training_cutoff is None or item.training_cutoff <= item.prediction_as_of
        for item in first.rows
    )
    assert first.baseline_summary.evaluated_count == 5
    assert first.model_summary.evaluated_count == 5


def test_rolling_origin_excludes_concurrent_unmatured_rows() -> None:
    history = tuple(dataset_row(i, 20 + i) for i in range(30))
    concurrent = dataset_row(30, 50)
    rows = history + tuple(concurrent for _ in range(12))

    report = evaluate_rolling_origin(
        rows,
        initial_history_rows=30,
        gbt_params={"n_estimators": 10, "num_leaves": 7},
    )

    assert all(
        row.training_cutoff is None or row.training_cutoff <= row.prediction_as_of
        for row in report.rows
    )


def test_rolling_origin_records_censored_outcome_without_scoring_it() -> None:
    rows = tuple(dataset_row(i, 20 + i, censored=i == 29) for i in range(30))
    report = evaluate_rolling_origin(
        rows,
        initial_history_rows=25,
        gbt_params={"n_estimators": 10, "num_leaves": 7},
    )
    censored = [item for item in report.rows if item.status is EvaluationStatus.CENSORED]
    assert len(censored) == 2
    assert all(item.actual is None and item.absolute_error is None for item in censored)
    assert report.baseline_summary.censored_count == 1
    assert report.model_summary.censored_count == 1


def test_rolling_origin_rejects_insufficient_rows_and_bad_thresholds() -> None:
    rows = tuple(dataset_row(i, 20 + i) for i in range(5))
    with pytest.raises(ValueError, match="positive"):
        evaluate_rolling_origin(rows, initial_history_rows=0)
    with pytest.raises(ValueError, match="at least one target"):
        evaluate_rolling_origin(rows, initial_history_rows=5)
    with pytest.raises(ValueError, match="cannot be negative"):
        assess_model_acceptance(
            summary(ForecastModelKind.BASELINE, "0.2"),
            summary(ForecastModelKind.GBT, "0.1"),
            (),
            required_improvement=Decimal("-0.1"),
        )
