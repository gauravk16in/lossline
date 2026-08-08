"""Tests for the revenue-at-risk estimator."""

from decimal import Decimal

import pytest

from lossline_intelligence.scoring.revenue_risk import (
    RevenueInputs,
    RevenueStatus,
    estimate_revenue_at_risk,
)


def _inputs(**overrides) -> RevenueInputs:
    base = dict(
        observed_cancelled_value=Decimal("1500"),
        current_cancel_rate=0.18,
        baseline_cancel_rate=0.07,
        current_order_rate_per_min=2.0,
        avg_order_value=Decimal("350"),
        currency="INR",
        forecast_horizon_minutes=60,
    )
    base.update(overrides)
    return RevenueInputs(**base)


def test_valid_inputs_return_ok_status() -> None:
    result = estimate_revenue_at_risk(_inputs())
    assert result.status is RevenueStatus.OK
    assert result.estimated_amount == Decimal("6120.00")
    assert result.currency == "INR"
    assert result.is_estimate is True
    assert result.formula_version == "revenue_risk.v2"
    assert result.assumptions
    assert result.components["avg_order_value"] == Decimal("350")


def test_total_exposure_equals_observed_plus_projected() -> None:
    result = estimate_revenue_at_risk(_inputs())
    assert result.display_total_exposure == (
        result.observed_cancelled_value + result.projected_revenue_at_risk
    )


def test_no_excess_cancel_rate_means_zero_projected() -> None:
    """When current <= baseline, projected exposure is zero."""
    result = estimate_revenue_at_risk(
        _inputs(current_cancel_rate=0.07, baseline_cancel_rate=0.07)
    )
    assert result.projected_revenue_at_risk == Decimal("0")
    assert result.excess_cancel_rate == 0.0


def test_zero_excess_cancellations_returns_zero_estimate_without_observed_loss() -> None:
    result = estimate_revenue_at_risk(
        _inputs(
            observed_cancelled_value=Decimal("0"),
            current_cancel_rate=0.04,
            baseline_cancel_rate=0.07,
        )
    )

    assert result.status is RevenueStatus.OK
    assert result.estimated_amount == Decimal("0.00")


def test_zero_avg_order_value_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(avg_order_value=Decimal("0")))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


def test_missing_avg_order_value_returns_unavailable_without_inventing_amount() -> None:
    result = estimate_revenue_at_risk(_inputs(avg_order_value=None))

    assert result.status is RevenueStatus.INSUFFICIENT_DATA
    assert result.estimated_amount is None
    assert result.components == {}
    assert result.reason == "avg_order_value is missing"
    assert result.is_estimate is True


def test_empty_currency_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(currency=""))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


def test_negative_order_rate_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(current_order_rate_per_min=-1.0))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observed_cancelled_value", Decimal("-0.01")),
        ("current_cancel_rate", -0.01),
        ("current_cancel_rate", 1.01),
        ("baseline_cancel_rate", -0.01),
        ("baseline_cancel_rate", 1.01),
        ("current_order_rate_per_min", -0.01),
        ("avg_order_value", Decimal("-1")),
        ("forecast_horizon_minutes", -1),
    ],
)
def test_negative_or_out_of_range_values_are_unavailable(field, value) -> None:
    result = estimate_revenue_at_risk(_inputs(**{field: value}))

    assert result.status is RevenueStatus.INSUFFICIENT_DATA
    assert result.estimated_amount is None


def test_deterministic_arithmetic() -> None:
    """Verify formula: projected = rate * horizon * avg_value * excess_rate."""
    result = estimate_revenue_at_risk(
        _inputs(
            current_cancel_rate=0.18,
            baseline_cancel_rate=0.07,
            current_order_rate_per_min=2.0,
            avg_order_value=Decimal("350"),
            forecast_horizon_minutes=60,
        )
    )
    # excess = 0.11, projected = 2.0 * 60 * 350 * 0.11 = 4620
    expected_projected = Decimal("2.0") * Decimal("60") * Decimal("350") * Decimal("0.11")
    assert abs(result.projected_revenue_at_risk - expected_projected) < Decimal("0.01")
