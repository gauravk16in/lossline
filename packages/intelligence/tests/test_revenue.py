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


def test_zero_avg_order_value_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(avg_order_value=Decimal("0")))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


def test_empty_currency_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(currency=""))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


def test_negative_order_rate_returns_insufficient() -> None:
    result = estimate_revenue_at_risk(_inputs(current_order_rate_per_min=-1.0))
    assert result.status is RevenueStatus.INSUFFICIENT_DATA


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
