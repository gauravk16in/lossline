from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dataclasses import replace

import pytest
from pydantic import ValidationError

from lossline_intelligence.forecasting import ForecastResult
from lossline_intelligence.outcomes import (
    ActualOutcome, ActualOutcomeStatus, OutcomeAbstention, OutcomeAbstentionReason,
    evaluate_decision_outcome, evaluate_forecast_outcome, evaluate_risk_predictions,
    mature_actual_outcome,
)

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc); T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc); T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def forecast():
    return ForecastResult(forecast_id="fc1", outlet_id="out1", sku_id="sku1",
        service_window="DINNER", prediction_as_of=T0, window_start=T1, window_end=T2,
        point_demand=Decimal("50"), lower_demand=Decimal("40"), upper_demand=Decimal("60"),
        interval_method="test", model_version="m1", feature_snapshot_id="snap1",
        data_sufficient=True, quality_flags=())


def mature(**changes):
    values = dict(forecast=forecast(), now=T2 + timedelta(minutes=30),
        actual_demand=Decimal("55"), fulfilled_quantity=Decimal("50"),
        unfulfilled_quantity=Decimal("5"), ending_inventory=Decimal("0"),
        capacity_utilization=Decimal("1.1"), status=ActualOutcomeStatus.AVAILABLE,
        source_ids=("event1",))
    values.update(changes); return mature_actual_outcome(**values)


def test_not_mature_at_below_and_mature_at_boundary() -> None:
    result = mature(now=T2 + timedelta(minutes=29, seconds=59))
    assert isinstance(result, OutcomeAbstention) and result.reason is OutcomeAbstentionReason.NOT_MATURE
    assert isinstance(mature(), ActualOutcome)


def test_available_outcome_conservation_and_forecast_metrics() -> None:
    outcome = mature(); evaluation = evaluate_forecast_outcome(forecast(), outcome)
    assert evaluation.absolute_error == Decimal("5.0000")
    assert evaluation.signed_error == Decimal("-5.0000")
    assert evaluation.interval_hit and evaluation.shortage_occurred


def test_censored_and_missing_not_scored() -> None:
    censored = mature(status=ActualOutcomeStatus.CENSORED)
    missing = mature(status=ActualOutcomeStatus.MISSING, actual_demand=None,
        fulfilled_quantity=None, unfulfilled_quantity=None)
    assert evaluate_forecast_outcome(forecast(), censored) is None
    assert evaluate_forecast_outcome(forecast(), missing) is None


def test_invalid_missing_conservation_nonfinite_and_duplicate_sources() -> None:
    with pytest.raises(ValidationError, match="missing outcome"):
        mature(status=ActualOutcomeStatus.MISSING)
    with pytest.raises(ValidationError, match="must equal"):
        mature(actual_demand=Decimal("56"))
    with pytest.raises(ValidationError, match="finite"):
        mature(actual_demand=Decimal("NaN"))
    with pytest.raises(ValidationError, match="unique"):
        mature(source_ids=("e1", "e1"))


def test_grain_mismatch_rejected() -> None:
    outcome = mature()
    with pytest.raises(ValueError, match="grain/window"):
        evaluate_forecast_outcome(replace(forecast(), sku_id="other"), outcome)


def test_decision_evaluation_is_association_only() -> None:
    result = evaluate_decision_outcome(decision_id="dec1", manager_decision="APPROVE", outcome=mature())
    assert result.observed_shortage is True
    assert "does not establish causation" in result.association_note


def test_risk_precision_recall_f1_and_zero_denominators() -> None:
    result = evaluate_risk_predictions(((True, True), (True, False), (False, True), (False, False)))
    assert (result.true_positive, result.false_positive, result.true_negative, result.false_negative) == (1, 1, 1, 1)
    assert result.precision == result.recall == result.f1 == Decimal("0.5000")
    empty_positive = evaluate_risk_predictions(((False, False),))
    assert empty_positive.precision is None and empty_positive.recall is None and empty_positive.f1 is None


def test_repeatable_identity_ignores_recheck_time() -> None:
    first = mature(now=T2 + timedelta(minutes=30)); second = mature(now=T2 + timedelta(minutes=60))
    assert first.outcome_id == second.outcome_id


def test_naive_now_and_negative_maturity_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"): mature(now=datetime(2026, 1, 7))
    with pytest.raises(ValueError, match="non-negative"): mature(maturity_delay_minutes=-1)
