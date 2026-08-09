"""Expanding-window baseline-versus-GBT forecast evaluation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from lossline_intelligence.evaluation.forecast import (
    EVALUATION_VERSION,
    EvaluationStatus,
    ForecastEvaluationReport,
    ForecastEvaluationRow,
    ForecastModelKind,
    assess_model_acceptance,
    compare_subgroups,
    compute_metric_summary,
    compute_report_id,
    demand_band,
)
from lossline_intelligence.features.snapshot import DatasetRow
from lossline_intelligence.forecasts import (
    BaselineAbstention,
    GBTAbstention,
    forecast_baseline,
    forecast_gbt,
    train_gbt_model,
)


ROLLING_SPLIT_VERSION = "expanding_window.v1"
_DP = Decimal("0.0001")


def _evaluation_id(
    model_kind: ForecastModelKind, snapshot_id: str, forecast_id: str | None
) -> str:
    encoded = json.dumps(
        {
            "forecast_id": forecast_id,
            "model_kind": model_kind.value,
            "snapshot_id": snapshot_id,
            "version": EVALUATION_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"evalrow_{sha256(encoded).hexdigest()[:20]}"


def _record(
    *,
    target: DatasetRow,
    model_kind: ForecastModelKind,
    forecast: Any | None,
    training_cutoff: datetime | None,
    abstention_reason: str | None,
) -> ForecastEvaluationRow:
    snapshot = target.snapshot
    if target.censored:
        status = EvaluationStatus.CENSORED
    elif forecast is None:
        status = EvaluationStatus.ABSTAINED
    else:
        status = EvaluationStatus.EVALUATED

    forecast_id = None if forecast is None else forecast.forecast_id
    prediction = None if forecast is None else forecast.point_demand
    lower = None if forecast is None else forecast.lower_demand
    upper = None if forecast is None else forecast.upper_demand
    actual = Decimal(target.target_demand_quantity) if status is EvaluationStatus.EVALUATED else None
    signed = prediction - actual if prediction is not None and actual is not None else None
    absolute = abs(signed) if signed is not None else None
    percentage = (
        None
        if actual is None or actual == 0 or absolute is None
        else (absolute / actual).quantize(_DP, rounding=ROUND_HALF_UP)
    )
    hit = (
        lower <= actual <= upper
        if lower is not None and actual is not None and upper is not None
        else None
    )
    return ForecastEvaluationRow(
        evaluation_id=_evaluation_id(model_kind, snapshot.snapshot_id, forecast_id),
        evaluation_version=EVALUATION_VERSION,
        model_kind=model_kind,
        forecast_id=forecast_id,
        model_version=None if forecast is None else (
            forecast.forecast_version if hasattr(forecast, "forecast_version") else forecast.model_version
        ),
        training_cutoff=training_cutoff,
        prediction_as_of=snapshot.window_start,
        window_start=snapshot.window_start,
        window_end=snapshot.window_end,
        outlet_id=snapshot.outlet_id,
        sku_id=snapshot.sku_id,
        service_window=snapshot.service_window,
        demand_band=demand_band(actual) if actual is not None else None,
        status=status,
        prediction=prediction,
        lower_bound=lower,
        upper_bound=upper,
        actual=actual,
        absolute_error=absolute,
        percentage_error=percentage,
        signed_error=signed,
        interval_hit=hit,
        abstention_reason=abstention_reason,
    )


def evaluate_rolling_origin(
    rows: Sequence[DatasetRow],
    *,
    initial_history_rows: int = 25,
    sku_categories: Mapping[str, str] | None = None,
    gbt_params: dict[str, Any] | None = None,
    gbt_test_fraction: float = 0.20,
    gbt_min_train_rows: int = 20,
) -> ForecastEvaluationReport:
    """Retrain on each expanding history and evaluate the next chronological row."""

    if initial_history_rows < 1:
        raise ValueError("initial_history_rows must be positive")
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                row.snapshot.window_start,
                row.snapshot.outlet_id,
                row.snapshot.sku_id,
            ),
        )
    )
    if len(ordered) <= initial_history_rows:
        raise ValueError("rows must contain at least one target after initial history")

    evaluation_rows: list[ForecastEvaluationRow] = []
    for index in range(initial_history_rows, len(ordered)):
        target = ordered[index]
        as_of = target.snapshot.window_start
        history = tuple(
            row
            for row in ordered[:index]
            if row.snapshot.window_end <= as_of
        )

        baseline_result = forecast_baseline(
            target.snapshot,
            history,
            prediction_as_of=as_of,
            sku_categories=sku_categories,
        )
        if isinstance(baseline_result, BaselineAbstention):
            evaluation_rows.append(
                _record(
                    target=target,
                    model_kind=ForecastModelKind.BASELINE,
                    forecast=None,
                    training_cutoff=None,
                    abstention_reason=baseline_result.reason.value,
                )
            )
        else:
            cutoff = max(
                row.snapshot.window_end
                for row in history
                if row.snapshot.snapshot_id in baseline_result.source_snapshot_ids
            )
            evaluation_rows.append(
                _record(
                    target=target,
                    model_kind=ForecastModelKind.BASELINE,
                    forecast=baseline_result,
                    training_cutoff=cutoff,
                    abstention_reason=None,
                )
            )

        artifact = train_gbt_model(
            history,
            test_fraction=gbt_test_fraction,
            params=gbt_params,
            min_train_rows=gbt_min_train_rows,
        )
        gbt_result = forecast_gbt(target.snapshot, artifact, prediction_as_of=as_of)
        if isinstance(gbt_result, GBTAbstention):
            evaluation_rows.append(
                _record(
                    target=target,
                    model_kind=ForecastModelKind.GBT,
                    forecast=None,
                    training_cutoff=None if artifact is None else artifact.training_cutoff,
                    abstention_reason=gbt_result.reason.value,
                )
            )
        else:
            evaluation_rows.append(
                _record(
                    target=target,
                    model_kind=ForecastModelKind.GBT,
                    forecast=gbt_result,
                    training_cutoff=artifact.training_cutoff if artifact else None,
                    abstention_reason=None,
                )
            )

    frozen_rows = tuple(evaluation_rows)
    baseline_summary = compute_metric_summary(frozen_rows, ForecastModelKind.BASELINE)
    model_summary = compute_metric_summary(frozen_rows, ForecastModelKind.GBT)
    subgroups = compare_subgroups(frozen_rows)
    acceptance = assess_model_acceptance(baseline_summary, model_summary, subgroups)
    return ForecastEvaluationReport(
        report_id=compute_report_id(frozen_rows),
        evaluation_version=EVALUATION_VERSION,
        split_strategy=ROLLING_SPLIT_VERSION,
        rows=frozen_rows,
        baseline_summary=baseline_summary,
        model_summary=model_summary,
        subgroup_comparisons=subgroups,
        acceptance=acceptance,
    )
